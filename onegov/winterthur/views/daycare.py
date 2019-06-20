from onegov.core.security import Public
from onegov.winterthur import WinterthurApp, _
from onegov.winterthur.daycare import DaycareSubsidyCalculator
from onegov.winterthur.daycare import DaycareSubsidyCalculatorForm
from onegov.winterthur.layout import DaycareSubsidyCalculatorLayout


@WinterthurApp.form(
    model=DaycareSubsidyCalculator,
    form=DaycareSubsidyCalculatorForm,
    permission=Public,
    template='daycare.pt')
def view_daycare_subsidy_calculator(self, request, form):

    if form.submitted(request):
        request.success(_("Calculation successful"))

    return {
        'title': _("Daycare Subsidy Calculator"),
        'layout': DaycareSubsidyCalculatorLayout(self, request),
        'form': form,
    }
