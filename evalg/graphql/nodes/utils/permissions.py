
import logging
import functools


from flask import current_app

from sqlalchemy.sql import and_
from graphene.types.resolver import get_default_resolver
from flask_sqlalchemy.model import camel_to_snake_case
from flask_allows import Permission

from evalg.utils import Name2Callable
from evalg.models.election import Election, ElectionGroup
from evalg.models.election_result import ElectionResult
from evalg.models.election_list import ElectionList
from evalg.graphql.nodes.utils.base import (get_session,
                                            get_current_user)
from evalg.authorization.permissions import IsElectionGroupAdmin, IsVisible

all_permissions = Name2Callable()
logger = logging.getLogger(__name__)


@all_permissions
def deny(*args, **kwargs):
    return False


@all_permissions
def allow(*args, **kwargs):
    return True


@all_permissions
def is_visible(session, user, source, **args):
    return Permission(
        IsVisible(source),
        identity=user,
    )


@all_permissions
def can_manage_election_group(session, user, election_group, **args):
    if hasattr(election_group, 'id'):
        return Permission(
            IsElectionGroupAdmin(session, election_group.id),
            identity=user)
    else:
        return Permission(
            IsElectionGroupAdmin(session, args.get('id')),
            identity=user)


@all_permissions
def can_manage_election(session, user, election, **args):
    return Permission(
        IsElectionGroupAdmin(session, election.group_id),
        identity=user
    )


@all_permissions
def can_manage_election_list(session, user, **args):
    election_list = None
    if 'list_id' in args:
        logger.error(args.get('list_id'))
        election_list = session.query(ElectionList).get(args.get('list_id'))
    return Permission(
        IsElectionGroupAdmin(session, election_list.election.group_id),
        identity=user
    )


@all_permissions
def can_access_election_result(session, user, election_result, **args):
    if hasattr(election_result, 'election'):
        election = election_result.election
    else:
        election = session.query(ElectionGroup).join(
            ElectionResult,
            and_(
                ElectionResult.election_id == Election.id,
                ElectionResult.id == args.get('id')
            )
        ).one()
    return Permission(
        IsElectionGroupAdmin(session, election.group_id),
        identity=user)


@all_permissions
def can_access_election_group_count(session, user, election_group_count,
                                    **args):
    return Permission(
        IsElectionGroupAdmin(session, election_group_count.group_id),
        identity=user
    )


@functools.lru_cache(maxsize=1)
def get_permissions_config():
    return current_app.config.get('PERMISSIONS')


def can_access_field(source, info, **args):
    """Checks if the requested field can be accessed by the user

    :type info: graphql.execution.base.ResolveInfo
    """
    session = get_session(info)
    user = get_current_user(info)
    permissions = get_permissions_config()['ObjectTypes'].get(
        str(info.parent_type))
    if 'Fields' not in permissions.keys():
        return False
    field_name = camel_to_snake_case(info.field_name)
    permission = permissions['Fields'].get(field_name)
    if all_permissions.get(permission, deny)(session, user, source,
                                             **args):
        return True
    return False


def permission_control_field(resolver):
    permission_control_field.decorated_resolvers.append(
        resolver.__name__
    )

    @functools.wraps(resolver)
    def wrapper(source, info, **args):
        logger.debug(info.parent_type)
        if can_access_field(source, info, **args):
            return resolver(source, info, **args)
        return None

    return wrapper


# For testing permission control
permission_control_field.decorated_resolvers = []


def permission_controlled_default_resolver(attname, default_value, root, info,
                                           **args):
    if can_access_field(root, info, **args):
        return get_default_resolver()(attname, default_value, root, info,
                                      **args)
    return None


def permission_control_single_resolver(permission_func):
    def decorate(resolver):
        @functools.wraps(resolver)
        def wrapper(source, info, **args):
            session = get_session(info)
            user = get_current_user(info)
            if permission_func(session, user, source, **args):
                return resolver(source, info, **args)
            return None

        return wrapper

    return decorate
