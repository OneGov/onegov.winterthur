import textwrap
import yaml

from babel.numbers import format_decimal
from cached_property import cached_property
from collections import defaultdict
from collections import OrderedDict
from decimal import Decimal
from functools import partial
from onegov.core.utils import Bunch
from onegov.core.utils import normalize_for_url
from onegov.directory import DirectoryCollection
from onegov.directory import DirectoryEntryCollection
from onegov.org.models import Organisation


SERVICE_DAYS = {
    'mo': 0,
    'di': 1,
    'mi': 2,
    'do': 3,
    'fr': 4,
    'sa': 5,
    'so': 6,
}


class Daycare(object):

    def __init__(self, id, title, rate, weeks):
        self.id = id
        self.title = title
        self.rate = rate
        self.weeks = weeks


class Services(object):

    def __init__(self, definition):
        self.available = OrderedDict()
        self.selected = defaultdict(set)

    @staticmethod
    def parse_definition(definition):
        for service in yaml.safe_load(definition):
            service_id = normalize_for_url(service['title'])

            yield service_id, Bunch(
                title=service['titel'],
                percentage=Decimal(service['percentage']),
                days={SERVICE_DAYS[d.lower()[:2]] for d in service['tage']}
            )

    def select(self, service_id, day):
        self.selected[service_id].add(day)

    def deselect(self, service_id, day):
        self.selected[service_id].remove(day)


class Result(object):

    def __init__(self, title, amount=None, note=None, operation=None):
        self.title = title
        self.amount = amount
        self.note = textwrap.dedent(note or '').strip(' \n')
        self.operation = operation


class Block(object):

    def __init__(self, title):
        self.title = title
        self.results = []
        self.total = Decimal(0)

    def op(self, title, amount=None, note=None, operation=None):
        if operation in (None, '+'):
            assert amount is not None
            self.total += amount

        elif operation == '=':
            assert amount is None
            amount = self.total

        elif operation == '-':
            assert amount is not None
            self.total -= amount

        elif operation in ('*', 'x', '×', '⋅'):
            assert amount is not None
            self.total *= amount

        elif operation in ('/', '÷'):
            assert amount is not None
            self.total /= amount

        self.results.append(Result(
            title=title,
            amount=amount,
            note=note,
            operation=operation,
        ))


class DirectoryDaycareAdapter(object):

    def __init__(self, directory):
        self.directory = directory

    @cached_property
    def fieldmap(self):
        fieldmap = {
            'daycare_rate': None,
            'daycare_weeks': None,
            'daycare_url': None,
        }

        for field in self.directory.basic_fields:

            if 'tagestarif' in field.label.lower():
                fieldmap['daycare_rate'] = field.name
                continue

            if 'öffnungswochen' in field.label.lower():
                fieldmap['daycare_weeks'] = field.name
                continue

            if 'webseite' in field.label.lower():
                fieldmap['daycare_url'] = field.name
                continue

        return fieldmap

    def as_daycare(self, entry):
        Daycare(
            id=entry.id,
            title=entry.title,
            daycare_rate=getattr(entry, self.fieldmap['daycare_rate']),
            daycare_weeks=getattr(entry, self.fieldmap['daycare_weeks']),
        )


class DaycareSubsidyCalculator(object):

    def __init__(self, session):
        self.session = session

    @cached_property
    def organisation(self):
        return self.session.query(Organisation).one()

    @cached_property
    def settings(self):
        return Bunch(**self.organisation.meta.get('daycare_settings'))

    @cached_property
    def directory(self):
        return DirectoryCollection(self.session).by_id(self.settings.directory)

    @cached_property
    def daycares(self):
        adapter = DirectoryDaycareAdapter(self.directory)

        items = DirectoryEntryCollection(self.directory).query()
        items = (i for i in items if not i.meta.get('is_hidden_from_public'))
        items = {i.id.hex: adapter.as_daycare(i) for i in items}

        return items

    def calculate(self, center, services, income, wealth, rebate):
        """ Creates a detailed calculation of the subsidy paid by Winterthur.

        The reslt is a list of tables with explanations.

        :param center:
            The selected daycare center (a :class:`Daycare` instance).

        :param services:
            Services used (a :class:`Services` instance)

        :param income:
            The income as a decimal.

        :param wealth:
            The wealth as decimal.

        :param rebate:
            True if a rebate is applied
        """

        cfg = self.settings
        fmt = partial(format_decimal, locale='de_CH')

        basis = Block("Berechnungsgrundlage für die Elternbeiträge")
        basis.op(
            title="Steuerbares Einkommen",
            amount=income,
            note="""
                Steuerbares Einkommen gemäss letzter Veranlagung
            """)

        basis.op(
            title="Vermögenszuschlag",
            amount=max((wealth - cfg.max_wealth) * cfg.wealth_premium, 0),
            note=f"""
                Der Vermögenszuschlag beträgt {fmt(cfg.wealth_premium)} des
                Vermögens, für das tatsächlich Steuern anfallen
                (ab {fmt(cfg.max_wealth)} CHF).
            """)

        basis.op(
            title="Massgebendes Gesamteinkommen",
            operation="=")

        basis.op(
            title="Abzüglich Minimaleinkommen",
            operation="-",
            amount=cfg.min_income)

        basis.op(
            title="Berechnungsgrundlage",
            operation="=")

        return [
            basis
        ]
