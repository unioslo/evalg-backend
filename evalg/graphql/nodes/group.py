"""
GraphQL ObjectType representing user groups.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.group
import evalg.proc.group
from evalg.graphql.nodes.base import get_session


# TODO:
#   resolve_group_search argument should be renamed from *val* to *search_term*
#   or similar.

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   evalg.group in order to show or mutate objects.


class Group(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.group.Group


def resolve_group_search(_, info, **args):
    """
    Search for groups by name
    """
    session = get_session(info)
    return evalg.proc.group.search_group(session, args['val'])


search_groups_query = graphene.List(
    Group,
    resolver=resolve_group_search,
    val=graphene.Argument(graphene.String, required=True))
