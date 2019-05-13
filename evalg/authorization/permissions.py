#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import logging

from flask_allows import Permission, Requirement

logger = logging.getLogger(__name__)


def get_principals_for(person):
    # TODO: could and should cache here
    principals = []
    principals.append(person.principal)
    # for group in person.groups
    #     find group principal
    #     principals.append(group.principal)
    return [x for x in principals if x is not None]


def role_in_principals(principals, **match):
    assert 'target_type' in match
    assert 'name' in match
    for principal in principals:
        for role in principal.roles:
            if all([getattr(role, k) == v for k, v in match.items()]):
                return True
    return False


class IsElectionGroupAdmin(Requirement):
    def __init__(self, election_group_id):
        self.election_group_id = election_group_id

    def fulfill(self, user):
        principals = get_principals_for(user.person)
        return role_in_principals(
            principals,
            target_type='election-group-role',
            name='admin',
            group_id=self.election_group_id)


def can_manage_election_group(user, election_group_id):
    return Permission(
        IsElectionGroupAdmin(election_group_id),
        identity=user)
