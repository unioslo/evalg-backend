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
from evalg.proc.group import get_user_groups
from evalg.utils import flask_request_memoize


def get_or_create_principal(session, principal_type, **kwargs):
    """
    Ensure existence of a principal.
    """
    lookup_opts = {
        'person': (PersonPrincipal, {
            'person_id': kwargs.get('person_id'),
        }),
        'person_identifier': (PersonIdentifierPrincipal, {
            'id_type': kwargs.get('id_type'),
            'id_value': kwargs.get('id_value'),
        }),
        'group': (GroupPrincipal, {
            'group_id': kwargs.get('group_id'),
        })
    }
    assert principal_type in lookup_opts
    principal_cls, selectors = lookup_opts.get(principal_type)
    assert all([v is not None for k, v in selectors.items()])
    principal = evalg.database.query.get_or_create(
        session,
        principal_cls,
        **selectors,
    )
    session.add(principal)
    session.flush()
    return principal


def get_principals_for_group(session, group):
    """Get all principals for a group."""
    return session.query(GroupPrincipal).filter(
        GroupPrincipal.group_id == group.id).all()


@flask_request_memoize
def get_principals_for_person(session, person):
    principals = []
    if person.principal:
        principals.append(person.principal)
    identifier_principals = get_person_identifier_principals(
        session, person).all()
    if identifier_principals:
        principals.extend(identifier_principals)

    for group in get_user_groups(session, person):
        group_principals = get_principals_for_group(session, group)
        if group_principals:
            principals.extend(group_principals)
    return [x for x in principals if x is not None]


def get_roles_for_person(session, person):
    principals = get_principals_for_person(session, person)
    roles = []
    for principal in principals:
        for role in principal.roles:
            roles.append(role)
    return roles


def get_person_roles_matching(session, person, **match):
    assert 'target_type' in match
    assert 'name' in match
    roles = get_roles_for_person(session, person)
    return [role for role in roles
            if all([getattr(role, k) == v for k, v in match.items()])]


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


def get_role_by_grant_id(session, grant_id):
    """
    Get a role by its grant ID. Returns `None` if not found.
    """
    return evalg.database.query.lookup_or_none(
        session,
        evalg.models.authorization.Role,
        grant_id=grant_id)


def delete_role(session, role):
    """
    Delete a role.
    """
    session.delete(role)
    session.flush()


def add_election_group_role(session, election_group, principal,
                            role_name, global_role=False):
    """
    Add an election group role.
    """
    role = evalg.database.query.get_or_create(
        session,
        ElectionGroupRole,
        name=role_name,
        principal=principal,
        group=election_group,
        global_role=global_role)
    session.add(role)
    session.flush()
    return role
