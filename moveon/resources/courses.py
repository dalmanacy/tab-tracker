from .base import ExternalIdMixin, Resource


class Courses(ExternalIdMixin, Resource):
    RESOURCE = "courses"
