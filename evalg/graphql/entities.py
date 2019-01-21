from graphene import String, Field, List, Boolean
from graphene_sqlalchemy import SQLAlchemyObjectType

import evalg.models.authorization
import evalg.models.candidate
import evalg.models.election
import evalg.models.election_list
import evalg.models.group
import evalg.models.person
import evalg.models.pollbook
import evalg.models.voter
from evalg.metadata import group_announcement_blockers
from evalg.metadata import group_publication_blockers
from evalg.utils import convert_json

# Must simply be imported in order to make our conversions apply
from . import converter  # noqa: F401


class Candidate(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.candidate.Candidate

    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)


class ElectionGroup(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election.ElectionGroup

    def resolve_meta(self, info):
        return convert_json(self.meta)

    announcement_blockers = List(String)
    publication_blockers = List(String)
    published = Boolean()
    announced = Boolean()

    def resolve_announcement_blockers(self, info):
        return group_announcement_blockers(self)

    def resolve_publication_blockers(self, info):
        return group_publication_blockers(self)


class ElectionList(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election_list.ElectionList


class Person(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.Person


class Group(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.group.Group


class PollBook(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.pollbook.PollBook


class Election(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election.Election

    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)

    pollbooks = List(PollBook)


class Voter(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.voter.Voter


class PersonPrincipal(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.PersonPrincipal


class GroupPrincipal(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.GroupPrincipal


class Principal(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.Principal

    person = Field(Person)
    group = Field(Group)


class ElectionRole(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.ElectionRole


class ElectionRoleList(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.ElectionRoleList


class ElectionGroupRole(SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.authorization.ElectionGroupRole
