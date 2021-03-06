"""
GraphQL ObjectType representing users.
"""
import logging
import graphene
import graphene_sqlalchemy

import evalg.proc.authz
import evalg.proc.person
import evalg.proc.pollbook
import evalg.proc.vote
import evalg.models.person
import evalg.authentication.user
import evalg.database.query
from evalg.graphql.nodes.utils.permissions import (
    permission_controlled_default_resolver,
    permission_controller,
)
from evalg.graphql.nodes.utils.base import get_session
from evalg.graphql.nodes.roles import Role

# TODO:
#   resolve_person_search argument should be renamed from *val* to
#   *search_term* or similar.

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   evalg.proc.person in order to show or mutate objects.

logger = logging.getLogger(__name__)


@permission_controller.control_object_type
class PersonIdentifier(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.PersonExternalId
        default_resolver = permission_controlled_default_resolver


@permission_controller.control_object_type
class Person(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.Person
        default_resolver = permission_controlled_default_resolver

    identifiers = graphene.List(PersonIdentifier)


def resolve_get_person_for_voter(_, info, **kwargs):
    voter_id = kwargs['voter_id']
    session = get_session(info)
    voter = evalg.database.query.lookup(
        session,
        evalg.models.voter.Voter,
        id=voter_id)
    return evalg.proc.pollbook.get_person_for_voter(session, voter)


get_person_for_voter_query = graphene.Field(
    Person,
    voter_id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_get_person_for_voter)


class Viewer(graphene.ObjectType):
    """
    A representation of the current user.
    """
    person = graphene.Field(Person)
    roles = graphene.List(Role)

    def resolve_person(self, info):
        return info.context['user'].person

    def resolve_roles(self, info):
        session = get_session(info)
        person = info.context['user'].person
        return evalg.proc.authz.get_roles_for_person(session, person)


def resolve_viewer_from_context(_, info):
    return info.context['user']


get_current_viewer_query = graphene.Field(
    Viewer,
    resolver=resolve_viewer_from_context)
