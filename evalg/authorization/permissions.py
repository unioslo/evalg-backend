#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import logging

from flask_allows import Permission, Requirement

from evalg.proc.authz import get_principals_for_person

logger = logging.getLogger(__name__)


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


def can_manage_election_group(session, user, election_group_id):
    return Permission(
        IsElectionGroupAdmin(session, election_group_id),
        identity=user)
