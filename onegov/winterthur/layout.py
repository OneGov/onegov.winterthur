from cached_property import cached_property
from onegov.org.layout import DefaultLayout
from onegov.core.elements import Link, LinkGroup, Intercooler
from onegov.winterthur import _
from onegov.winterthur.collections import AddressCollection
from onegov.winterthur.collections import MissionReportVehicleCollection
from onegov.winterthur.roadwork import RoadworkCollection


class AddressLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Addresses"), '#'),
        ]

    @cached_property
    def editbar_links(self):
        if not self.request.is_manager:
            return

        return [
            Link(
                text=_("Update"),
                url=self.csrf_protected_url(
                    self.request.link(self.model, '+update')
                ),
                attrs={'class': 'sync'},
                traits=Intercooler(
                    request_method='POST',
                    redirect_after=self.request.url
                )
            )
        ]


class AddressSubsetLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Addresses"), self.request.class_link(AddressCollection)),
            Link(_(self.model.street), '#')
        ]


class RoadworkCollectionLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Roadworks"), '#'),
        ]


class RoadworkLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Roadworks"), self.request.class_link(RoadworkCollection)),
            Link(self.model.title, self.request.link(self.model))
        ]


class MissionReportCollectionLayout(DefaultLayout):

    @cached_property
    def breadcrumbs(self):
        return [
            Link(_("Homepage"), self.homepage_url),
            Link(_("Mission Reports"), '#'),
        ]

    @cached_property
    def editbar_links(self):
        if not self.request.is_manager:
            return

        return [
            Link(
                _("Vehicles"), self.request.class_link(
                    MissionReportVehicleCollection
                ), attrs={'class': 'vehicles'}
            ),
            LinkGroup(
                title=_("Add"),
                links=[
                    Link(
                        text=_("Mission Report"),
                        url=self.request.link(
                            self.model,
                            name='+new'
                        ),
                        attrs={'class': 'new-report'}
                    )
                ]
            ),
        ]
