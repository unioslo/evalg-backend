"""
GraphQL ObjectType representing users.
"""
import logging
import graphene
import graphene_sqlalchemy

import evalg.proc.authz
import evalg.proc.person
import evalg.proc.vote
import evalg.models.person
import evalg.authentication.user
import evalg.database.query
from evalg.graphql.nodes.utils import permissions
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


class PersonIdentifier(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.PersonExternalId


class Person(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.Person
        default_resolver = permissions.permission_controlled_default_resolver

    identifiers = graphene.List(PersonIdentifier)


def resolve_persons_by_info(_, info):
    return Person.get_query(info).all()


def resolve_person_by_id(_, info, **args):
    return Person.get_query(info).get(args['id'])


def resolve_person_search(_, info, **args):
    # TODO: arg should be renamed *search_term* or somethign similar
    session = get_session(info)
    return evalg.proc.person.search_persons(session, args['val'])


def resolve_get_person_for_voter(_, info, **args):
    voter_id = args['voter_id']
    session = get_session(info)
    voter = evalg.database.query.lookup(
        session,
        evalg.models.voter.Voter,
        id=voter_id)
    return evalg.proc.vote.get_person_for_voter(session, voter)


list_persons_query = graphene.List(
    Person,
    resolver=resolve_persons_by_info)

get_person_query = graphene.Field(
    Person,
    resolver=resolve_person_by_id,
    id=graphene.Argument(graphene.UUID, required=True))

search_persons_query = graphene.List(
    Person,
    resolver=resolve_person_search,
    val=graphene.Argument(graphene.String, required=True))


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
