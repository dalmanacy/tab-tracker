from .base import ExternalIdMixin, Resource


class CatalogueCourses(ExternalIdMixin, Resource):
    RESOURCE = "catalogue-courses"
