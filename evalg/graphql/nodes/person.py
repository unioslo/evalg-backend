"""
GraphQL ObjectType representing users.
"""
import graphene
import graphene_sqlalchemy

import evalg.person
import evalg.proc.vote
import evalg.models.person
import evalg.authentication.user
import evalg.database.query
from evalg.graphql.nodes.base import get_session

# TODO:
#   resolve_person_search argument should be renamed from *val* to
#   *search_term* or similar.

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   evalg.person in order to show or mutate objects.


class PersonIdentifier(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.PersonExternalId


class Person(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.Person

    identifiers = graphene.List(PersonIdentifier)


def resolve_persons_by_info(_, info):
    return Person.get_query(info).all()


def resolve_person_by_id(_, info, **args):
    return Person.get_query(info).get(args['id'])


def resolve_person_search(_, info, **args):
    # TODO: arg should be renamed *search_term* or somethign similar
    return evalg.person.search_person(args['val'])


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

    Is there any reason we don't simply write an alternate resolver for the
    Person object? Is there a reason for wrapping this in another ObjectType?
    """
    person = graphene.Field(Person)

    def resolve_person(self, info):
        return info.context['user'].person


def resolve_viewer_from_context(_, info):
    return info.context['user']


get_current_viewer_query = graphene.Field(
    Viewer,
    resolver=resolve_viewer_from_context)
