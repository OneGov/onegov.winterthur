from onegov.core.elements import Link
from onegov.core.security import Public, Private
from onegov.winterthur import WinterthurApp, _
from onegov.winterthur.collections import MissionReportCollection
from onegov.winterthur.collections import MissionReportVehicleCollection
from onegov.winterthur.forms import MissionReportForm
from onegov.winterthur.forms import MissionReportVehicleForm
from onegov.winterthur.layout import MissionReportLayout
from onegov.winterthur.models import MissionReport
from onegov.winterthur.models import MissionReportVehicle


def mission_report_form(model, request):
    if isinstance(model, MissionReportCollection):
        report = MissionReport()
    else:
        report = model

    return report.with_content_extensions(MissionReportForm, request)


def mission_report_vehicle_form(model, request):
    if isinstance(model, MissionReportVehicleCollection):
        report = MissionReportVehicle()
    else:
        report = model

    return report.with_content_extensions(MissionReportVehicleForm, request)


@WinterthurApp.html(
    model=MissionReportCollection,
    permission=Public,
    template='mission_reports.pt')
def view_mission_reports(self, request):

    return {
        'layout': MissionReportLayout(self, request),
        'title': _("Mission Reports"),
        'reports': self.batch,
    }


@WinterthurApp.html(
    model=MissionReport,
    permission=Public,
    template='mission_report.pt')
def view_mission(self, request):
    return {
        'title': self.title,
        'layout': MissionReportLayout(
            self, request,
            Link(self.title, '#')
        ),
        'model': self,
    }


@WinterthurApp.html(
    model=MissionReportVehicleCollection,
    permission=Public,
    template='mission_report_vehicles.pt')
def view_mission_report_vehicles(self, request):

    return {
        'layout': MissionReportLayout(
            self, request,
            Link(_("Vehicles"), request.link(self))
        ),
        'title': _("Vehicles"),
        'vehicles': self.query(),
    }


@WinterthurApp.form(
    model=MissionReportCollection,
    permission=Private,
    form=mission_report_form,
    name='new',
    template='form.pt')
def handle_new_mission_report(self, request, form):

    if form.submitted(request):
        mission = self.add(**{
            k: v for k, v in form.data.items() if k != 'csrf_token'})

        request.success(_("Successfully added a mission report"))
        return request.redirect(request.link(mission))

    return {
        'title': _("Mission Reports"),
        'form': form,
        'layout': MissionReportLayout(
            self, request,
            Link(_("New"), '#', editbar=False)
        ),
    }


@WinterthurApp.form(
    model=MissionReport,
    permission=Private,
    form=mission_report_form,
    name='edit',
    template='form.pt')
def handle_edit_mission_report(self, request, form):

    if form.submitted(request):
        form.populate_obj(self)

        request.success(_("Your changes were saved"))
        return request.redirect(request.link(self))

    elif not request.POST:
        form.process(obj=self)

    return {
        'title': _("Mission Reports"),
        'form': form,
        'layout': MissionReportLayout(
            self, request,
            Link(self.title, request.link(self)),
            Link(_("Edit"), '#', editbar=False),
        )
    }


@WinterthurApp.form(
    model=MissionReportVehicleCollection,
    permission=Private,
    form=mission_report_vehicle_form,
    name='new',
    template='form.pt')
def handle_new_vehicle(self, request, form):

    if form.submitted(request):
        vehicle = self.add(
            **{k: v for k, v in form.data.items() if k not in (
                'csrf_token', 'symbol'
            )})

        # required for the symbol image
        form.populate_obj(vehicle)

        request.success(_("Successfully added a vehicle"))

        return request.redirect(
            request.class_link(MissionReportVehicleCollection))

    return {
        'title': _("Vehicle"),
        'form': form,
        'layout': MissionReportLayout(
            self, request,
            Link(_("Vehicles"), request.link(self)),
            Link(_("New"), '#', editbar=False)
        ),
    }


@WinterthurApp.form(
    model=MissionReportVehicle,
    permission=Private,
    form=mission_report_vehicle_form,
    name='edit',
    template='form.pt')
def handle_edit_vehicle(self, request, form):

    if form.submitted(request):
        form.populate_obj(self)

        request.success(_("Your changes were saved"))

        return request.redirect(
            request.class_link(MissionReportVehicleCollection))

    elif not request.POST:
        form.process(obj=self)

    return {
        'title': _("Vehicle"),
        'form': form,
        'layout': MissionReportLayout(
            self, request,
            Link(_("Vehicles"), request.class_link(
                MissionReportVehicleCollection)),
            Link(self.title, request.link(self)),
            Link(_("Edit"), '#', editbar=False),
        )
    }
