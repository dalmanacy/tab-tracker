from .base import ExternalIdMixin, Resource


class Persons(ExternalIdMixin, Resource):
    RESOURCE = "persons"
