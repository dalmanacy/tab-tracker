from .base import ExternalIdMixin, Resource


class ExternalInstitutions(ExternalIdMixin, Resource):
    RESOURCE = "external-institutions"
