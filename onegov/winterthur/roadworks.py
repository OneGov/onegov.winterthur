import pycurl

from cached_property import cached_property
from datetime import datetime, timedelta
from io import BytesIO
from onegov.core.custom import json
from pathlib import Path


class RoadworksError(Exception):
    pass


class RoadworksConnectionError(RoadworksError):
    pass


class RoadworksConfig(object):
    """ Looks at ~/.pdb.secret and /etc/pdb.secret (in this order), to extract
    the configuration used for the RoadworksClient class.

    The configuration is as follows::

        HOSTNAME: pdb.example.org
        ENDPOINT: 127.0.0.1:6004
        USERNAME: username
        PASSWORD: password

    * The HOSTNAME is the address of the PDB service.
    * The ENDPOINT is the optional address of the tcp-proxy used.
    * The USERNAME is the NTLM password.
    * The PASSWORD is the NTLM password.

    """

    def __init__(self, hostname, endpoint, username, password):
        self.hostname = hostname
        self.endpoint = endpoint
        self.username = username
        self.password = password

    @classmethod
    def lookup_paths(self):
        yield Path('~/.pdb.secret').expanduser()
        yield Path('/etc/pdb.secret')

    @classmethod
    def lookup(cls):
        for path in cls.lookup_paths():
            if path.exists():
                return cls(**cls.parse(path))

        paths = ', '.join(str(p) for p in cls.lookup_paths())
        raise RoadworksError(
            f"No pdb configuration found in {paths}")

    @classmethod
    def parse(cls, path):
        result = {
            'hostname': None,
            'endpoint': None,
            'username': None,
            'password': None,
        }

        with path.open('r') as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                if ':' not in line:
                    continue

                if line.startswith('#'):
                    continue

                k, v = line.split(':', maxsplit=1)
                k = k.strip().lower()
                v = v.strip()

                if k in result:
                    result[k] = v

        return result


class RoadworksClient(object):
    """ A proxy to Winterthur's internal roadworks service. Uses redis as
    a caching mechanism to ensure performance and reliability.

    Since the roadworks service can only be reached inside Winterthur's
    network, we rely on a proxy connection during development/testing.

    To not expose any information unwittingly to the public, the description
    of how to connect to that proxy is kept at docs.seantis.ch.

    """

    def __init__(self, cache, hostname, username, password, endpoint=None):
        self.cache = cache
        self.hostname = hostname
        self.username = username
        self.password = password
        self.endpoint = endpoint or hostname

    @cached_property
    def curl(self):
        curl = pycurl.Curl()
        curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_NTLM)
        curl.setopt(pycurl.USERPWD, f"{self.username}:{self.password}")
        curl.setopt(pycurl.HTTPHEADER, [f'HOST: {self.hostname}'])

        return curl

    def url(self, path):
        return f'http://{self.endpoint}/{path}'

    def get(self, path, lifetime=5 * 60, downtime=60 * 60):
        """ Requests the given path, returning the resulting json if
        successful.

        A cache is used in two stages:

        * At the lifetime stage, the cache is returned unconditionally.
        * At the end of the lifetime, the cache is refreshed if possible.
        * At the end of the downtime stage the cache forcefully refreshed.

        During its lifetime the object is basically up to 5 minutes out of
        date. But since the backend may not be available when that time
        expires we operate with a downtime that is higher (1 hour).

        This means that a downtime in the backend will not result in evicted
        caches, even if the lifetime is up. Once the downtime limit is up we
        do however evict the cache forcefully, raising an error if we cannot
        connect to the backend.

        """

        cached = self.cache.get(path)

        def refresh():
            try:
                status, body = self.get_uncached(path)
            except pycurl.error:
                raise RoadworksConnectionError(
                    f"Could not connect to {self.hostname}")

            if status == 200:
                self.cache.set(path, {
                    'created': datetime.utcnow(),
                    'status': status,
                    'body': body
                })

                return body

            raise RoadworksError(f"{path} returned {status}")

        # no cache yet, return result and cache it
        if not cached:
            return refresh()

        now = datetime.utcnow()
        lifetime_horizon = cached['created'] + timedelta(seconds=lifetime)
        downtime_horizon = cached['created'] + timedelta(seconds=downtime)

        # within cache lifetime, return cached value
        if now <= lifetime_horizon:
            return cached['body']

        # outside cache lifetime, but still in downtime horizon, try to
        # refresh the value but ignore errors
        if lifetime_horizon < now < downtime_horizon:
            try:
                return refresh()
            except RoadworksConnectionError:
                return cached['body']

        # outside the downtime lifetime, force refresh and raise errors
        return refresh()

    def get_uncached(self, path):
        body = BytesIO()

        self.curl.setopt(pycurl.URL, self.url(path))
        self.curl.setopt(pycurl.WRITEFUNCTION, body.write)
        self.curl.perform()

        status = self.curl.getinfo(pycurl.RESPONSE_CODE)
        body = body.getvalue().decode('utf-8')

        if status == 200:
            body = json.loads(body)

        return status, body

    def is_cacheable(self, response):
        return response[0] == 200


class RoadworksCollection(object):

    def __init__(self, client):
        self.client = client

    @property
    def letters(self):
        return [
            item["Letter"] for item in
            self.client.get('odata/getBaustellenIndex').get('value', ())
        ]
