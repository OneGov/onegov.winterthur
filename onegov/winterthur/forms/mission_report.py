from onegov.form import Form
from onegov.form.fields import TimezoneDateTimeField
from onegov.winterthur import _
from wtforms.fields import BooleanField
from wtforms.fields import StringField
from wtforms.fields import TextAreaField
from wtforms.fields.html5 import DecimalField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import InputRequired
from wtforms.validators import NumberRange


class MissionReportForm(Form):

    date = TimezoneDateTimeField(
        _("Date"),
        timezone='Europe/Zurich',
        validators=[InputRequired()])

    duration = DecimalField(
        _("Mission duration"),
        validators=[InputRequired(), NumberRange(0, 10000)])

    nature = TextAreaField(
        _("Mission nature"),
        render_kw={'rows': 4},
        validators=[InputRequired()])

    location = StringField(
        _("Location"),
        validators=[InputRequired()])

    personnel = IntegerField(
        _("Mission Personnel"),
        validators=[InputRequired(), NumberRange(0, 10000)])

    backup = IntegerField(
        _("Backup Personnel"),
        validators=[InputRequired(), NumberRange(0, 10000)])

    civil_defence = BooleanField(
        _("Civil Defence Involvement"))
