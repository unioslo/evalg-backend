#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import logging
from flask_allows import Requirement as OriginalRequirement

from evalg.proc.authz import (get_principals_for_person,
                              get_person_roles_matching)
from evalg.proc.pollbook import get_voters_for_person
from evalg.proc.group import get_election_key_meta
from evalg.utils import flask_request_memoize


logger = logging.getLogger(__name__)


class Requirement(OriginalRequirement):
    def __call__(self, user):
        # TODO: Workaround to avoid warnings. Remove when this is merged:
        #       https://github.com/justanr/flask-allows/pull/45
        return self.fulfill(user)


@flask_request_memoize
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

    @flask_request_memoize
    def fulfill(self, user):
        principals = get_principals_for_person(self.session, user.person)
        return role_in_principals(
            principals,
            target_type='election-group-role',
            name='admin',
            group_id=self.election_group_id)


class IsPerson(Requirement):
    def __init__(self, person):
        self.person = person

    @flask_request_memoize
    def fulfill(self, user):
        return user.person.id == self.person.id


class HasPersonCreatedMyElectionsKey(Requirement):
    def __init__(self, session, person):
        self.person = person
        self.session = session

    @flask_request_memoize
    def fulfill(self, user):
        user_roles = get_person_roles_matching(
            self.session,
            user.person,
            target_type='election-group-role',
            name='admin'
        )
        for user_role in user_roles:
            key_meta = get_election_key_meta(self.session, user_role.group_id)
            if not key_meta:
                return False
            generated_by = key_meta[0].transaction.user
            if generated_by.id == self.person.id:
                return True
        return False


class IsVoter(Requirement):
    def __init__(self, session, voter):
        self.session = session
        self.voter = voter

    @flask_request_memoize
    def fulfill(self, user):
        return self.voter.id in [
            v.id for v in get_voters_for_person(
                self.session,
                user.person
            ).all()
        ]


class IsPublisher(Requirement):
    def __init__(self, session):
        self.session = session

    @flask_request_memoize
    def fulfill(self, user, request=None):
        principals = get_principals_for_person(self.session, user.person)
        return role_in_principals(
            principals,
            target_type='election-group-role',
            name='publisher',
            global_role=True
        )
