import chameleon
import textwrap
import yaml

from babel.numbers import format_decimal
from cached_property import cached_property
from collections import defaultdict
from collections import OrderedDict
from decimal import Decimal, localcontext
from onegov.core.utils import Bunch
from onegov.core.utils import normalize_for_url
from onegov.directory import DirectoryCollection
from onegov.directory import DirectoryEntryCollection
from onegov.form import Form
from onegov.org.models import Organisation
from onegov.winterthur import _
from ordered_set import OrderedSet
from wtforms.fields import Field
from wtforms.validators import InputRequired, ValidationError
from wtforms.widgets.core import HTMLString


SERVICE_DAYS = {
    'mo': 0,
    'di': 1,
    'mi': 2,
    'do': 3,
    'fr': 4,
    'sa': 5,
    'so': 6,
}

SERVICE_DAYS_LABELS = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}


def round_to_5_cents(n):
    """ Rounds a number to 5 cents. """

    return int(n / Decimal('0.05') + Decimal('0.5')) * Decimal('0.05')


class Daycare(object):

    def __init__(self, id, title, rate, weeks):
        self.id = id
        self.title = title
        self.rate = rate
        self.weeks = weeks

    @property
    def factor(self):
        """ Currently not really specified anywhere, just taken from the
        existing solution. Why this is 4.25 is unclear.

        """
        return Decimal(self.weeks * (4.25 / 51))


class Services(object):

    def __init__(self, definition):
        if definition:
            self.available = OrderedDict(self.parse_definition(definition))
        else:
            self.available = OrderedDict()

        self.selected = defaultdict(set)

    @classmethod
    def from_org(cls, org):
        if 'daycare_settings' not in org.meta:
            return cls(None)

        if 'services' not in org.meta['daycare_settings']:
            return cls(None)

        return cls(org.meta['daycare_settings']['services'])

    @classmethod
    def from_session(cls, session):
        return cls.from_org(session.query(Organisation).one())

    @staticmethod
    def parse_definition(definition):
        for service in yaml.safe_load(definition):
            service_id = normalize_for_url(service['titel'])
            days = (d.strip() for d in service['tage'].split(','))

            yield service_id, Bunch(
                id=service_id,
                title=service['titel'],
                percentage=Decimal(service['prozent']),
                days=OrderedSet(SERVICE_DAYS[d.lower()[:2]] for d in days),
            )

    def select(self, service_id, day):
        self.selected[service_id].add(day)

    def deselect(self, service_id, day):
        self.selected[service_id].remove(day)

    def is_selected(self, service_id, day):
        if service_id not in self.selected:
            return False

        return day in self.selected[service_id]

    @property
    def total(self):
        """ Returns the total percentage of used services. """
        return sum(
            self.available[s].percentage * len(self.selected[s])
            for s in self.selected
        )


class Result(object):

    def __init__(self, title,
                 amount=None, note=None, operation=None, bold=False):

        self.title = title
        self.amount = amount
        self.note = textwrap.dedent(note or '').strip(' \n')
        self.operation = operation
        self.bold = bold


class Block(object):

    def __init__(self, title):
        self.title = title
        self.results = []
        self.total = Decimal(0)

    def op(self, title,
            amount=None, note=None, operation=None, bold=False, round=False):

        transform = round and round_to_5_cents or (lambda a: a)

        if operation in (None, '+'):
            assert amount is not None
            self.total += transform(amount)

        elif operation == '=':
            assert amount is None
            amount = transform(self.total)

        elif operation == '-':
            assert amount is not None
            self.total -= transform(amount)

        elif operation in ('*', 'x', '×', '⋅'):
            assert amount is not None
            self.total *= transform(amount)

        elif operation in ('/', '÷'):
            assert amount is not None
            self.total /= transform(amount)

        self.results.append(Result(
            title=title,
            amount=transform(amount),
            note=note,
            operation=operation,
            bold=bold,
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
                fieldmap['daycare_rate'] = field.id
                continue

            if 'öffnungswochen' in field.label.lower():
                fieldmap['daycare_weeks'] = field.id
                continue

            if 'webseite' in field.label.lower():
                fieldmap['daycare_url'] = field.id
                continue

        return fieldmap

    def as_daycare(self, entry):
        return Daycare(
            id=entry.id,
            title=entry.title,
            rate=entry.values[self.fieldmap['daycare_rate']],
            weeks=entry.values[self.fieldmap['daycare_weeks']],
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

    def daycare_by_title(self, title):
        return next(d for d in self.daycares.values() if d.title == title)

    def calculate(self, *args, **kwargs):
        with localcontext() as ctx:
            ctx.prec = 5

            return self.calculate_precisely(*args, **kwargs)

    def calculate_precisely(self, daycare, services, income, wealth, rebate):
        """ Creates a detailed calculation of the subsidy paid by Winterthur.

        The reslt is a list of tables with explanations.

        :param daycare:
            The selected daycare (a :class:`Daycare` instance).

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

        def fmt(amount):

            # babel needs its own decimal context, or it throws errors
            with localcontext() as ctx:
                ctx.prec = 28
                return format_decimal(amount, locale='de_CH')

        # Base Rate
        # ---------
        base = Block("Berechnungsgrundlage für die Elternbeiträge")

        base.op(
            title="Steuerbares Einkommen",
            amount=income,
            note="""
                Steuerbares Einkommen gemäss letzter Veranlagung
            """)

        base.op(
            title="Vermögenszuschlag",
            amount=max((wealth - cfg.max_wealth) * cfg.wealth_premium, 0),
            operation="+",
            note=f"""
                Der Vermögenszuschlag beträgt {fmt(cfg.wealth_premium)} des
                Vermögens, für das tatsächlich Steuern anfallen
                (ab {fmt(cfg.max_wealth)} CHF).
            """)

        base.op(
            title="Massgebendes Gesamteinkommen",
            operation="=")

        base.op(
            title="Abzüglich Minimaleinkommen",
            operation="-",
            amount=cfg.min_income)

        base.op(
            title="Berechnungsgrundlage",
            operation="=")

        # Gross Contribution
        # ------------------
        gross = Block("Berechnung des Brutto-Elternbeitrags")

        gross.op(
            title="Übertrag",
            amount=base.total)

        gross.op(
            title="Faktor",
            amount=cfg.wealth_factor,
            operation="×",
            note="""
                Ihr Elternbeitrag wird aufgrund eines Faktors berechnet
                (Kita-Reglement Art. 20 Abs 3)
            """)

        gross.op(
            title="Einkommensabhängiger Elternbeitragsbestandteil",
            operation="=")

        gross.op(
            title="Mindestbeitrag Eltern",
            amount=cfg.min_rate,
            operation="+")

        gross.op(
            title="Elternbeitrag brutto",
            operation="=")

        # Rebate
        # ------
        rebate = gross.total * cfg.rebate / 100 if rebate else 0

        net = Block("Berechnung des Rabatts")

        net.op(
            title="Übertrag",
            amount=gross.total)

        net.op(
            title="Rabatt",
            amount=rebate,
            operation="-",
            note=f"""
                Bei einem Betreuungsumfang von insgesamt mehr als 2 ganzen
                Tagen pro Woche gilt ein Rabatt von {cfg.rebate}%.
            """)

        net.op(
            title="Elternbeitrag netto",
            operation="=")

        # Actual contribution
        # -------------------
        actual = Block(
            "Berechnung des Elternbeitrags und des "
            "städtischen Beitrags pro Tag")

        actual.op(
            title="Übertrag",
            amount=net.total)

        actual.op(
            title="Zusatzbeitrag Eltern",
            amount=max(daycare.rate - cfg.max_rate, 0),
            operation="+",
            note=f"""
                Zusatzbeitrag für Kitas, deren Tagestarif über
                {cfg.max_rate} CHF liegt.
            """)

        actual.op(
            title="Elternbeitrag pro Tag",
            operation="=",
            note="""
                Ihr Beitrag pro Tag (100%) und Kind
            """,
            bold=True)

        actual.op(
            title="Städtischer Beitrag pro Tag",
            amount=rebate,
            note="""
                Städtischer Beitrag für Ihr Kind pro Tag
            """)

        # Monthly contribution
        # --------------------
        monthly = Block(
            "Berechnung des Elternbeitrags und des städtischen Beitrags "
            "pro Monat (Monatspauschale)")

        monthly.op(
            title="Wochentarif",
            amount=(actual.total - rebate) * services.total / 100,
            note="""
                Wochentarif: Elternbeiträge der gewählten Betreuungstage
            """)

        monthly.op(
            title="Faktor",
            amount=daycare.factor,
            operation="×",
            note="""
                Faktor für jährliche Öffnungswochen Ihrer Kita
            """)

        monthly.op(
            title="Elternbeitrag pro Monat",
            operation="=",
            bold=True,
            round=True)

        monthly.op(
            title="Städtischer Beitrag pro Monat",
            amount=rebate * services.total / 100 * daycare.factor,
            note="""
                Städtischer Beitrag für Ihr Kind pro Tag
            """,
            round=True)

        return (base, gross, net, actual, monthly)


class DaycareServicesWidget(object):

    template = chameleon.PageTemplate("""
        <table class="daycare-services">
            <thead>
                <tr>
                    <th></th>
                    <th tal:repeat="service this.services.available.values()">
                        <div class="daycare-services-title">
                            ${service.title}
                        </div>
                        <div class="daycare-services-percentage">
                            ${service.percentage}%
                        </div>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr tal:repeat="day this.days">
                    <td>
                        <strong>${this.day_label(day)}</strong>
                    </td>
                    <td tal:repeat="svc this.services.available.values()">
                        <input
                            type="checkbox"

                            id="${svc.id}-${day}"
                            name="${this.field.name}"
                            value="${svc.id}-${day}"

                            tal:attributes="checked this.is_selected(svc, day)"
                        />
                    </td>
                </tr>
            </tbody>
        </table
    """)

    def __call__(self, field, **kwargs):
        self.field = field
        self.services = field.services

        return HTMLString(self.template.render(this=self))

    def is_selected(self, service, day):
        return self.services.is_selected(service.id, day)

    def day_label(self, day):
        return SERVICE_DAYS_LABELS[day]

    @property
    def days(self):
        days = OrderedSet()

        for service in self.services.available.values():
            for day in service.days:
                days.add(day)

        return days


class DaycareServicesField(Field):

    widget = DaycareServicesWidget()

    @cached_property
    def services(self):
        return Services.from_session(self.meta.request.session)

    def process_formdata(self, valuelist):
        for value in valuelist:
            service_id, day = value.rsplit('-', maxsplit=1)
            self.services.select(service_id, int(day))

    def pre_validate(self, form):
        for day in SERVICE_DAYS.values():
            days = sum(
                1 for id in self.services.available
                if self.services.is_selected(id, day)
            )

            if days > 1:
                raise ValidationError(
                    "Es gibt Überschneidungen bei den gewählten "
                    "Betreuungszeiten."
                )


class DaycareSubsidyCalculatorForm(Form):

    services = DaycareServicesField(
        label=_("Services"),
        validators=(InputRequired(), )
    )
