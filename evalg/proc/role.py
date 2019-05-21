#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module implements role maintenance.
"""

from collections import defaultdict

import evalg.database.query
from evalg.models.authorization import (ElectionGroupRole,
                                        GroupPrincipal,
                                        PersonPrincipal)
from evalg.models.election import ElectionGroup
from evalg.models.person import PersonExternalId


def get_or_create_principal(session, principal_type, principal_owner_id):
    """
    Ensure existence of a principal.
    """
    lookup_opts = {
        'person': (PersonPrincipal, 'person_id'),
        'group': (GroupPrincipal, 'group_id')
    }
    assert principal_type in lookup_opts
    principal_cls, selector_field = lookup_opts.get(principal_type)
    principal = evalg.database.query.get_or_create(
        session,
        principal_cls,
        **{selector_field: principal_owner_id},
    )
    session.add(principal)
    session.flush()
    return principal


def add_election_group_role(session, election_group, principal,
                            role_name):
    """
    Add an election group role.
    """
    role = evalg.database.query.get_or_create(
        session,
        ElectionGroupRole,
        name=role_name,
        principal=principal,
        group=election_group)
    session.add(role)
    session.flush()
    return role


def update_person(person, kwargs):
    identifiers = kwargs.pop('identifiers', {})
    if identifiers:
        current = defaultdict(set)
        map(lambda x: current[x.id_type].add(x.id_value),
            person.identifiers)
        for k, value in identifiers.items():
            if value not in current[k]:
                person.identifiers.append(
                    PersonExternalId(id_type=k, id_value=value))
    for k, v in kwargs.items():
        if hasattr(person, k) and getattr(person, k) != v:
            setattr(person, k, v)
    return person
