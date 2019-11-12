"""
GraphQL ObjectType representing user groups.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.group
import evalg.proc.group
from evalg.graphql.nodes.utils.base import get_session
from evalg.graphql.nodes.utils.permissions import (
    permission_controlled_default_resolver,
    permission_controller,
)


@permission_controller.control_object_type
class Group(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.group.Group
        default_resolver = permission_controlled_default_resolver
