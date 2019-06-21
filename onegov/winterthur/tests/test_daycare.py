import pytest
import textwrap
import transaction

from decimal import Decimal
from onegov.directory import DirectoryCollection
from onegov.directory import DirectoryConfiguration
from onegov.org.models import Organisation
from onegov.winterthur.daycare import DaycareSubsidyCalculator, Services


@pytest.fixture(scope='function')
def app(winterthur_app):
    app = winterthur_app

    session = app.session()

    dirs = DirectoryCollection(session, type='extended')
    directory = dirs.add(
        title="Daycare Centers",
        structure=textwrap.dedent("""
            Name *= ___
            Webseite = https://
            Tagestarif *= 0..1000
            Öffnungswochen *= 0..52
        """),
        configuration=DirectoryConfiguration(
            title="[Name]",
            order=('Name', ),
        ))

    # Some actual daycare centers in Winterthur
    directory.add(values=dict(
        name="Pinochio",
        tagestarif=98,
        offnungswochen=49,
        webseite="",
    ))

    directory.add(values=dict(
        name="Fantasia",
        tagestarif=108,
        offnungswochen=51,
        webseite="",
    ))

    directory.add(values=dict(
        name="Kinderhaus",
        tagestarif=110,
        offnungswochen=50,
        webseite="",
    ))

    directory.add(values=dict(
        name="Child Care Corner",
        tagestarif=125,
        offnungswochen=51,
        webseite="",
    ))

    directory.add(values=dict(
        name="Apfelblüte",
        tagestarif=107,
        offnungswochen=51,
        webseite="",
    ))

    org = session.query(Organisation).one()
    org.meta['daycare_settings'] = {
        'rebate': Decimal('5.00'),
        'max_rate': Decimal('107'),
        'min_rate': Decimal('15'),
        'max_income': Decimal('75000'),
        'max_wealth': Decimal('154000'),
        'min_income': Decimal('20000'),
        'wealth_factor': Decimal('0.0016727273'),
        'wealth_premium': Decimal('10.00'),
        'directory': directory.id.hex,
        'services': textwrap.dedent("""
            - titel: "Ganzer Tag inkl. Mitagessen"
              tage: "Montag, Dienstag, Mittwoch, Donnerstag, Freitag"
              prozent: 100.00

            - titel: "Vor- oder Nachmittag inkl. Mitagessen"
              tage: "Montag, Dienstag, Mittwoch, Donnerstag, Freitag"
              prozent: 75.00

            - titel: "Vor- oder Nachmittag ohne Mitagessen"
              tage: "Montag, Dienstag, Mittwoch, Donnerstag, Freitag"
              prozent: 50.00
        """)
    }

    transaction.commit()
    session.close_all()

    return app


def test_calculate_example_1(app):
    calculator = DaycareSubsidyCalculator(app.session())

    services = Services.from_org(app.org)
    services.select('ganzer-tag-inkl-mitagessen', 'mo')
    services.select('ganzer-tag-inkl-mitagessen', 'di')
    services.select('ganzer-tag-inkl-mitagessen', 'mi')
    services.select('ganzer-tag-inkl-mitagessen', 'do')
    services.select('ganzer-tag-inkl-mitagessen', 'fr')

    calculation = calculator.calculate(
        daycare=calculator.daycare_by_title("Fantasia"),
        services=services,
        income=Decimal('75000'),
        wealth=Decimal('150000'),
        rebate=True,
    )

    base, gross, net, actual, monthly = calculation.blocks

    results = [(r.title, r.operation, r.amount) for r in base.results]
    assert results == [
        ("Steuerbares Einkommen", None, Decimal('75000')),
        ("Vermögenszuschlag", "+", Decimal('0')),
        ("Massgebendes Gesamteinkommen", "=", Decimal('75000')),
        ("Abzüglich Minimaleinkommen", "-", Decimal('20000')),
        ("Berechnungsgrundlage", "=", Decimal('55000')),
    ]

    results = [(r.title, r.operation, r.amount) for r in gross.results]
    assert results == [
        ("Übertrag", None, Decimal('55000')),
        ("Faktor", "×", Decimal("0.0016727273")),
        ("Einkommensabhängiger Elternbeitragsbestandteil", "=", Decimal("92")),
        ("Mindestbeitrag Eltern", "+", Decimal("15")),
        ("Elternbeitrag brutto", "=", Decimal("107")),
    ]

    results = [(r.title, r.operation, r.amount) for r in net.results]
    assert results == [
        ("Übertrag", None, Decimal('107')),
        ("Rabatt", "-", Decimal('5.35')),
        ("Elternbeitrag netto", "=", Decimal('101.65')),
    ]

    results = [(r.title, r.operation, r.amount) for r in actual.results]
    assert results == [
        ("Übertrag", None, Decimal('101.65')),
        ("Zusatzbeitrag Eltern", "+", Decimal('1')),
        ("Elternbeitrag pro Tag", "=", Decimal('102.65')),
        ("Städtischer Beitrag pro Tag", None, Decimal('5.35'))
    ]

    results = [(r.title, r.operation, r.amount) for r in monthly.results]
    assert results == [
        ("Wochentarif", None, Decimal('513.25')),
        ("Faktor", "×", Decimal('4.25')),
        ("Elternbeitrag pro Monat", "=", Decimal('2181.30')),
        ("Städtischer Beitrag pro Monat", None, Decimal('113.69')),
    ]


def test_calculate_example_2(app):
    calculator = DaycareSubsidyCalculator(app.session())

    services = Services.from_org(app.org)
    services.select('ganzer-tag-inkl-mitagessen', 'mo')
    services.select('ganzer-tag-inkl-mitagessen', 'di')
    services.select('ganzer-tag-inkl-mitagessen', 'mi')
    services.select('ganzer-tag-inkl-mitagessen', 'do')
    services.select('ganzer-tag-inkl-mitagessen', 'fr')

    calculation = calculator.calculate(
        daycare=calculator.daycare_by_title("Apfelblüte"),
        services=services,
        income=Decimal('25000'),
        wealth=Decimal('0'),
        rebate=False,
    )

    base, gross, net, actual, monthly = calculation.blocks

    # note, these results slightly differ from the output, as the rounding
    # only happens when the numbers are rendered
    results = [(r.title, r.amount) for r in base.results]
    assert results == [
        ("Steuerbares Einkommen", Decimal('25000')),
        ("Vermögenszuschlag", Decimal('0')),
        ("Massgebendes Gesamteinkommen", Decimal('25000')),
        ("Abzüglich Minimaleinkommen", Decimal('20000')),
        ("Berechnungsgrundlage", Decimal('5000')),
    ]

    results = [(r.title, r.amount) for r in gross.results]
    assert results == [
        ("Übertrag", Decimal('5000')),
        ("Faktor", Decimal("0.0016727273")),
        ("Einkommensabhängiger Elternbeitragsbestandteil", Decimal("8.3636")),
        ("Mindestbeitrag Eltern", Decimal("15")),
        ("Elternbeitrag brutto", Decimal("23.364")),
    ]

    results = [(r.title, r.amount) for r in net.results]
    assert results == [
        ("Übertrag", Decimal('23.364')),
        ("Rabatt", Decimal('0')),
        ("Elternbeitrag netto", Decimal('23.364')),
    ]

    results = [(r.title, r.amount) for r in actual.results]
    assert results == [
        ("Übertrag", Decimal('23.364')),
        ("Zusatzbeitrag Eltern", Decimal('0')),
        ("Elternbeitrag pro Tag", Decimal('23.364')),
        ("Städtischer Beitrag pro Tag", Decimal('83.636'))
    ]

    results = [(r.title, r.amount) for r in monthly.results]
    assert results == [
        ("Wochentarif", Decimal('116.82')),
        ("Faktor", Decimal('4.2500')),
        ("Elternbeitrag pro Monat", Decimal('496.48')),
        ("Städtischer Beitrag pro Monat", Decimal('1777.3')),
    ]
