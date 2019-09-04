#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import logging
import functools

from flask import current_app

from sqlalchemy.sql import and_
from graphene.types.resolver import get_default_resolver
from flask_sqlalchemy.model import camel_to_snake_case
from flask_allows import Permission, Requirement as OriginalRequirement

from evalg.utils import Name2Callable
from evalg.models.election import Election, ElectionGroup
from evalg.models.election_result import ElectionResult
from evalg.models.election_list import ElectionList
from evalg.proc.authz import get_principals_for_person
from evalg.graphql.nodes.base import (get_session,
                                      get_current_user)

logger = logging.getLogger(__name__)
all_permissions = Name2Callable()


class Requirement(OriginalRequirement):
    def __call__(self, user):
        # TODO: Workaround to avoid warnings. Remove when this is merged:
        #       https://github.com/justanr/flask-allows/pull/45
        return self.fulfill(user)


def role_in_principals(principals, **match):
    assert 'target_type' in match
    assert 'name' in match
    for principal in principals:
        for role in principal.roles:
            if all([getattr(role, k) == v for k, v in match.items()]):
                return True
    return False


class IsElectionGroupAdmin(Requirement):
    def __init__(self, session, election_group_id):
        self.session = session
        self.election_group_id = election_group_id

    def fulfill(self, user):
        principals = get_principals_for_person(self.session, user.person)
        return role_in_principals(
            principals,
            target_type='election-group-role',
            name='admin',
            group_id=self.election_group_id)


class IsVisible(Requirement):
    def __init__(self, source):
        self.source = source

    def fulfill(self, user):
        if hasattr(self.source, 'election_status'):
            return self.source.election_status in ('announced', 'published',
                                                   'ongoing')
        elif hasattr(self.source, 'status'):
            return self.source.status in (
                'announced', 'published', 'ongoing')
        return False


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
        logger.error(user)
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
    logger.error(user.person)
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
        if can_access_field(source.id, info, **args):
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
