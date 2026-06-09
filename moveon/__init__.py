from .client import MoveOnClient
from .exceptions import MoveOnAPIError, MoveOnAuthError
from .resources import (
    AcademicYears,
    Addresses,
    BankAccounts,
    CatalogueCourses,
    Communications,
    ContactRoles,
    CourseUnits,
    Courses,
    DegreePrograms,
    ExternalContacts,
    ExternalInstitutions,
    Frameworks,
    Fundings,
    Grants,
    InternalContacts,
    InternalInstitutions,
    Payments,
    Persons,
    Prefilldata,
    ReferenceLists,
    RelationContacts,
    RelationContents,
    RelationInstitutions,
    Relations,
    Stays,
    SubjectAreas,
)


class MoveOn:
    """
    Entry point for the MoveOn API.

    Usage:
        mo = MoveOn(
            base_url="https://myinstance.restapi.moveonfr.com/api/v1/",
            username="user@example.com",
            password="secret",
        )
        mo.persons.list()
        mo.stays.get(42)
    """

    def __init__(self, base_url: str, username: str, password: str):
        client = MoveOnClient(base_url, username, password)
        self.academic_years        = AcademicYears(client)
        self.addresses             = Addresses(client)
        self.bank_accounts         = BankAccounts(client)
        self.catalogue_courses     = CatalogueCourses(client)
        self.communications        = Communications(client)
        self.contact_roles         = ContactRoles(client)
        self.course_units          = CourseUnits(client)
        self.courses               = Courses(client)
        self.degree_programs       = DegreePrograms(client)
        self.external_contacts     = ExternalContacts(client)
        self.external_institutions = ExternalInstitutions(client)
        self.frameworks            = Frameworks(client)
        self.fundings              = Fundings(client)
        self.grants                = Grants(client)
        self.internal_contacts     = InternalContacts(client)
        self.internal_institutions = InternalInstitutions(client)
        self.payments              = Payments(client)
        self.persons               = Persons(client)
        self.prefilldata           = Prefilldata(client)
        self.reference_lists       = ReferenceLists(client)
        self.relation_contacts     = RelationContacts(client)
        self.relation_contents     = RelationContents(client)
        self.relation_institutions = RelationInstitutions(client)
        self.relations             = Relations(client)
        self.stays                 = Stays(client)
        self.subject_areas         = SubjectAreas(client)


__all__ = [
    "MoveOn",
    "MoveOnClient",
    "MoveOnAPIError",
    "MoveOnAuthError",
]
