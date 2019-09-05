#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module
 - does
 - things
"""
import logging
from flask_allows import Requirement as OriginalRequirement

from evalg.proc.authz import get_principals_for_person
from evalg.proc.pollbook import get_voters_for_person

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


class IsPerson(Requirement):
    def __init__(self, person):
        self.person = person

    def fulfill(self, user):
        return user.person.id == self.person.id


class IsVoter(Requirement):
    def __init__(self, session, voter):
        self.session = session
        self.voter = voter

    def fulfill(self, user):
        if self.voter.id in [
            v.id for v in get_voters_for_person(self.session, user.person)
        ]:
            return True


class IsVisible(Requirement):
    def __init__(self, source):
        self.source = source

    def fulfill(self, user):
        if hasattr(self.source, 'election_status'):
            return self.source.election_status in ('announced', 'published',
                                                   'ongoing')
        if hasattr(self.source, 'status'):
            return self.source.status in (
                'announced', 'published', 'ongoing')
        return False
