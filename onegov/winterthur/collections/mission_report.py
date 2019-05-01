from onegov.core.collection import GenericCollection, Pagination
from onegov.winterthur.models import MissionReport
from onegov.winterthur.models import MissionReportVehicle
from sqlalchemy import or_


class MissionReportCollection(GenericCollection, Pagination):

    def __init__(self, session, page=0, include_hidden=False):
        self.session = session
        self.page = page
        self.include_hidden = include_hidden

    @property
    def model_class(self):
        return MissionReport

    def __eq__(self, other):
        return self.page == other.page

    def query(self):
        query = super().query()

        if not self.include_hidden:
            query = query.filter(or_(
                MissionReport.meta['is_hidden_from_public'] == False,
                MissionReport.meta['is_hidden_from_public'] == None
            ))

        return query

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

    def query(self):
        return super().query().order_by(MissionReportVehicle.name)