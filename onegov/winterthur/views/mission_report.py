from onegov.core.security import Public
from onegov.winterthur import WinterthurApp, _
from onegov.winterthur.collections import MissionReportCollection
from onegov.winterthur.layout import MissionReportCollectionLayout


@WinterthurApp.html(
    model=MissionReportCollection,
    permission=Public,
    template='mission_reports.pt')
def view_mission_reports(self, request):

    return {
        'layout': MissionReportCollectionLayout(self, request),
        'title': _("Mission Reports"),
        'reports': self.batch
    }
