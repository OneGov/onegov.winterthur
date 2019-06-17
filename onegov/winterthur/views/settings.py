import textwrap

from onegov.core.security import Secret
from onegov.directory import Directory, DirectoryCollection
from onegov.feriennet import _
from onegov.form import Form
from onegov.org.models import Organisation
from onegov.org.views.settings import handle_generic_settings
from onegov.winterthur.app import WinterthurApp
from yaml import safe_load
from yaml.error import YAMLError
from wtforms.fields import RadioField, TextAreaField
from wtforms.fields.html5 import DecimalField
from wtforms.validators import InputRequired, ValidationError


class WinterthurDaycareSettingsForm(Form):

    max_income = DecimalField(
        label=_("Maximum taxable income"),
        fieldset=_("Variables"),
        places=0,
        validators=[InputRequired()])

    max_wealth = DecimalField(
        label=_("Maximum taxable wealth"),
        fieldset=_("Variables"),
        places=0,
        validators=[InputRequired()])

    min_income = DecimalField(
        label=_("Minimum income"),
        fieldset=_("Variables"),
        places=0,
        validators=[InputRequired()])

    min_rate = DecimalField(
        label=_("Minimum day-rate"),
        fieldset=_("Variables"),
        places=0,
        validators=[InputRequired()])

    max_rate = DecimalField(
        label=_("Maximum day-rate"),
        fieldset=_("Variables"),
        places=0,
        validators=[InputRequired()])

    wealth_premium = DecimalField(
        label=_("Wealth premium (%)"),
        fieldset=_("Variables"),
        places=2,
        validators=[InputRequired()])

    wealth_factor = DecimalField(
        label=_("Factor"),
        fieldset=_("Variables"),
        places=10,
        validators=[InputRequired()])

    rebate = DecimalField(
        label=_("Rebate (%)"),
        fieldset=_("Variables"),
        places=2,
        validators=[InputRequired()])

    coverage = TextAreaField(
        fieldset=_("Variables"),
        validators=[InputRequired()],
        render_kw={'rows': 32, 'data-editor': 'yaml'})

    directory = RadioField(
        label=_("Directory"),
        fieldset=_("Institutions"),
        validators=[InputRequired()],
        choices=None)

    def populate_obj(self, obj, *args, **kwargs):
        super().populate_obj(obj, *args, **kwargs)
        obj.meta['daycare_settings'] = self.data

    def process_obj(self, obj):
        super().process_obj(obj)
        for k, v in obj.meta.get('daycare_settings', {}).items():
            getattr(self, k).data = v

        if not self.coverage.data.strip():
            self.coverage.data = textwrap.dedent("""
                # Beispiel:
                #
                # - titel: "Ganzer Tag inkl. Mitagessen"
                #   tage: "Montag, Dienstag, Mittwoch, Donnerstag, Freitag"
                #   prozent: 100.00
            """)

    def validate_coverage(self, field):
        try:
            safe_load(field.data)
        except YAMLError:
            raise ValidationError(_("Invalid yaml input"))

    def directory_choices(self):
        dirs = DirectoryCollection(self.request.session)

        def choice(directory):
            return (
                directory.id.hex,
                directory.title
            )

        for d in dirs.query().order_by(Directory.order):
            yield choice(d)

    def on_request(self):
        self.directory.choices = list(self.directory_choices())


@WinterthurApp.form(model=Organisation, name='daycare-settings',
                    template='form.pt', permission=Secret,
                    form=WinterthurDaycareSettingsForm, setting=_("Daycare"),
                    icon='fa-child')
def custom_handle_settings(self, request, form):
    return handle_generic_settings(self, request, form, _("Feriennet"))
