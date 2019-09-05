"""
GraphQL ObjectType representing user groups.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.group
import evalg.proc.group
from evalg.graphql.nodes.utils.base import get_session
from evalg.graphql.nodes.utils import permissions


class Group(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.group.Group
        default_resolver = permissions.permission_controlled_default_resolver


def resolve_group_search(_, info, **args):
    """
    Search for groups by name
    """
    session = get_session(info)
    return evalg.proc.group.search_groups(session, args['search_term']).all()


search_groups_query = graphene.List(
    Group,
    resolver=resolve_group_search,
    search_term=graphene.Argument(graphene.String, required=True))
