from onegov.core.collection import GenericCollection, Pagination
from onegov.winterthur.models import MissionReport
from onegov.winterthur.models import MissionReportVehicle


class MissionReportCollection(GenericCollection, Pagination):

    def __init__(self, session, page=0):
        self.session = session
        self.page = page

    @property
    def model_class(self):
        return MissionReport

    def __eq__(self, other):
        return self.page == other.page

    def subset(self):
        return self.query()

    @property
    def page_index(self):
        return self.page

    def page_by_index(self, index):
        return self.__class__(self.session, page=index)


class MissionReportVehicleCollection(GenericCollection):

    @property
    def model_class(self):
        return MissionReportVehicle
