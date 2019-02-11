"""
GraphQL ObjectType representing users.
"""
import graphene
import graphene_sqlalchemy

import evalg.person
import evalg.models.person
import evalg.authentication.user

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


class Person(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.person.Person


def resolve_persons_by_info(_, info):
    return Person.get_query(info).all()


def resolve_person_by_id(_, info, **args):
    return Person.get_query(info).get(args['id'])


def resolve_person_search(_, info, **args):
    # TODO: arg should be renamed *search_term* or somethign similar
    return evalg.person.search_person(args['val'])


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


class Viewer(graphene.ObjectType):
    """
    A representation of the current user.

    Is there any reason we don't simply write an alternate resolver for the
    Person object? Is there a reason for wrapping this in another ObjectType?
    """
    person = graphene.Field(Person)

    def resolve_person(self, info):
        return info.context.user.person


def resolve_viewer_from_context(_, info):
    return evalg.authentication.user


get_current_viewer_query = graphene.Field(
    Viewer,
    resolver=resolve_viewer_from_context)
