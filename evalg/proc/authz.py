#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module helps fethcing and manipulating authorization data
"""

from sqlalchemy import and_

import evalg.database.query
from evalg.models.authorization import (ElectionGroupRole,
                                        GroupPrincipal,
                                        PersonPrincipal)
from evalg.models.person import PersonExternalId
from evalg.models.authorization import PersonIdentifierPrincipal


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


def get_principals_for_person(session, person):
    # TODO: could and should cache here
    principals = []
    if person.principal:
        principals.append(person.principal)
    identifier_principals = get_person_identifier_principals(
        session, person).all()
    if identifier_principals:
        principals.extend(identifier_principals)
    # for group in person.groups
    #     find group principal
    #     principals.append(group.principal)
    return [x for x in principals if x is not None]


def get_person_identifier_principals(session, person):
    """
    Get all `PersonIdentifierPrincipal`s matching the external IDs of a person.
    """
    query = session.query(
        PersonIdentifierPrincipal
    ).join(
        PersonExternalId,
        person.id == PersonExternalId.person_id
    ).filter(
        and_(
            PersonIdentifierPrincipal.id_type == PersonExternalId.id_type,
            PersonIdentifierPrincipal.id_value == PersonExternalId.id_value,
        )
    )
    return query


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
