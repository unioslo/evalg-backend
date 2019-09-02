#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import json
import logging
import functools

from flask import current_app

from graphene.types.resolver import get_default_resolver
from flask_allows import Permission, Requirement as OriginalRequirement

from evalg.proc.authz import get_principals_for_person
from evalg.graphql.nodes.base import (get_session,
                                      get_current_user)


logger = logging.getLogger(__name__)


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


class Permissions(object):
    @staticmethod
    def deny(*args):
        return False

    @staticmethod
    def allow(*args):
        return True

    @staticmethod
    def can_manage_election_group(session, user, election_group_id):
        return Permission(
            IsElectionGroupAdmin(session, election_group_id),
            identity=user)


@functools.lru_cache(maxsize=1)
def get_permissions_config():
    with open(current_app.config.get('PERMISSIONS_PATH'),
              encoding='utf-8') as permissions_file:
        permissions = json.load(permissions_file)
    return permissions


def can_access_field(id, info):
    """Checks if the requested field can be accessed by the user

    :type info: graphql.execution.base.ResolveInfo
    """
    session = get_session(info)
    user = get_current_user(info)
    permissions = get_permissions_config().get(str(info.parent_type))
    if 'field_permissions' not in permissions.keys():
        return False
    permission = permissions['field_permissions'].get(info.field_name, '')
    if getattr(Permissions, permission, Permissions.deny)(session, user, id):
        return True
    return False


def permission_control_decorate(resolver):
    permission_control_decorate.decorated_resolvers.append(
        resolver.__name__
    )

    @functools.wraps(resolver)
    def wrapper(source, info, **args):
        if can_access_field(source.id, info):
            return resolver(source, info, **args)
        return None
    return wrapper


# For testing permission control
permission_control_decorate.decorated_resolvers = []


def permission_controlled_default_resolver(attname, default_value, root, info,
                                           **args):
    if can_access_field(root.id, info):
        return get_default_resolver()(attname, default_value, root, info,
                                      **args)
    return None
