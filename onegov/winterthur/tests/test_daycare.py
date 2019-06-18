import pytest
import textwrap
import transaction

from decimal import Decimal
from onegov.directory import DirectoryCollection
from onegov.directory import DirectoryConfiguration
from onegov.org.models import Organisation
from onegov.winterthur.daycare import DaycareSubsidyCalculator


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


def test_calculate_base(app):
    calculator = DaycareSubsidyCalculator(app.session())

    base, *_ = calculator.calculate(
        center=None,
        services=None,
        income=Decimal('75000'),
        wealth=Decimal('150000'),
        rebate=False,
    )

    assert base.total == Decimal('55000')
