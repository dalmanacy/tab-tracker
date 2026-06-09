from .base import ExternalIdMixin, Resource


class InternalInstitutions(ExternalIdMixin, Resource):
    RESOURCE = "internal-institutions"
