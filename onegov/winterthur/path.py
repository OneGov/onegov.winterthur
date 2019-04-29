from onegov.winterthur.app import WinterthurApp
from onegov.winterthur.collections import AddressCollection
from onegov.winterthur.collections import AddressSubsetCollection
from onegov.winterthur.collections import MissionReportCollection
from onegov.winterthur.collections import MissionReportVehicleCollection
from onegov.winterthur.models import MissionReport
from onegov.winterthur.models import MissionReportVehicle
from onegov.winterthur.roadwork import RoadworkCollection, Roadwork
from uuid import UUID


@WinterthurApp.path(
    model=AddressCollection,
    path='/streets')
def get_streets_directory(app):
    return AddressCollection(app.session())


@WinterthurApp.path(
    model=AddressSubsetCollection,
    path='/streets/{street}')
def get_street_subset(app, street):
    subset = AddressSubsetCollection(app.session(), street=street)
    return subset.exists() and subset or None


@WinterthurApp.path(
    model=RoadworkCollection,
    path='/roadwork')
def get_roadwork_collection(app, letter=None, query=None):
    return RoadworkCollection(app.roadwork_client, letter=letter, query=query)


@WinterthurApp.path(
    model=Roadwork,
    path='/roadwork/{id}',
    converters=dict(id=int))
def get_roadwork(app, id):
    return RoadworkCollection(app.roadwork_client).by_id(id)


@WinterthurApp.path(
    model=MissionReportCollection,
    path='/mission-reports')
def get_mission_reports(app, page=0):
    return MissionReportCollection(app.session(), page=page)


@WinterthurApp.path(
    model=MissionReportVehicleCollection,
    path='/mission-reports/vehicles')
def get_mission_report_vehicles(app):
    return MissionReportVehicleCollection(app.session())


@WinterthurApp.path(
    model=MissionReport,
    path='/mission-reports/report/{id}',
    converters=dict(id=UUID))
def get_mission_report(app, id):
    return get_mission_reports(app).by_id(id)


@WinterthurApp.path(
    model=MissionReportVehicle,
    path='/mission-reports/vehicle/{id}',
    converters=dict(id=UUID))
def get_mission_report_vehicle(app, id):
    return get_mission_report_vehicles(app).by_id(id)
