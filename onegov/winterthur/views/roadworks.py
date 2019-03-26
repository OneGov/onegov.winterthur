from onegov.core.security import Public
from onegov.winterthur import WinterthurApp, _
from onegov.winterthur.layout import RoadworksLayout
from onegov.winterthur.roadworks import RoadworksCollection


@WinterthurApp.html(
    model=RoadworksCollection,
    permission=Public,
    template='roadworks.pt'
)
def view_roadworks(self, request):

    return {
        'layout': RoadworksLayout(self, request),
        'title': _("Roadworks"),
        'model': self
    }
