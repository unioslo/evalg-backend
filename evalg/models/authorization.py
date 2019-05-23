"""
Database models for access control.

Basic idea:

* A user holds zero or more principals (i.e. has a user, and are member
  of groups)
* A principal maps to zero or more roles (e.g. being member of group
  «election board» leads to role «election board member».
* A role grants one or more permission.
* When doing a task, a permission is checked.
"""

import uuid

from sqlalchemy import types
from sqlalchemy.sql import schema
from sqlalchemy.orm import relationship, validates

from evalg.database.types import UuidType
from evalg.models.person import IdType as PersonIdType
from .base import ModelBase


class Principal(ModelBase):
    """
    Security principal.

    An evalg security principal is an abstract representation of an individual
    user or a group of users.
    """

    __tablename__ = 'principal'
    __versioned__ = {}

    id = schema.Column(
        UuidType,
        default=uuid.uuid4,
        primary_key=True)

    principal_type = schema.Column(
        types.String,
        nullable=False)

    roles = relationship(
        'Role',
        back_populates='principal')

    __mapper_args__ = {
        'polymorphic_identity': 'principal',
        'polymorphic_on': principal_type,
    }


class PersonPrincipal(Principal):
    """ Security principal based on a person/user entity. """

    __tablename__ = 'person_principal'
    __versioned__ = {}

    id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.id'),
        default=uuid.uuid4,
        primary_key=True)

    person_id = schema.Column(
        UuidType,
        schema.ForeignKey('person.id'),
        nullable=False,
        unique=True)

    person = relationship(
        'Person',
        back_populates='principal')

    __mapper_args__ = {
        'polymorphic_identity': 'person-principal',
        'inherit_condition': id == Principal.id,
    }


class PersonIdentifierPrincipal(Principal):
    """
    Security principal based on an external ID representing
    a person/user entity.
    """

    __tablename__ = 'person_identifier_principal'
    __versioned__ = {}

    id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.id'),
        default=uuid.uuid4,
        primary_key=True)

    id_type = schema.Column(
        types.UnicodeText,
        nullable=False)

    id_value = schema.Column(
        types.UnicodeText,
        nullable=False)

    @validates('id_type')
    def validate_id_type(self, key, id_type):
        return PersonIdType(id_type).value

    __table_args__ = (
        schema.UniqueConstraint('id_type', 'id_value'),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'person-identifier-principal',
        'inherit_condition': id == Principal.id,
    }


class GroupPrincipal(Principal):
    """ Security principal based on membership in a group. """

    __tablename__ = 'group_principal'
    __versioned__ = {}

    id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.id'),
        default=uuid.uuid4,
        primary_key=True)

    group_id = schema.Column(
        UuidType,
        schema.ForeignKey('group.id'),
        nullable=False)

    group = relationship(
        'Group',
        back_populates='principals')

    __mapper_args__ = {
        'polymorphic_identity': 'group-principal',
        'inherit_condition': id == Principal.id,
    }


class Role(ModelBase):
    """ Roles granted to a principal. """

    __tablename__ = 'role'
    __versioned__ = {}

    grant_id = schema.Column(
        UuidType,
        default=uuid.uuid4,
        primary_key=True)

    name = schema.Column(
        types.String,
        nullable=False)

    target_type = schema.Column(
        types.String(50),
        nullable=False)

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.id'),
        nullable=False)

    principal = relationship(
        'Principal',
        back_populates='roles')

    __mapper_args__ = {
        'polymorphic_identity': 'role',
        'polymorphic_on': target_type
    }


class ElectionGroupRole(Role):
    """ Roles granted on election. """

    __tablename__ = 'election_group_role'
    __versioned__ = {}

    grant_id = schema.Column(
        UuidType,
        schema.ForeignKey('role.grant_id'),
        default=uuid.uuid4,
        primary_key=True)

    group_id = schema.Column(
        UuidType,
        schema.ForeignKey('election_group.id'))

    group = relationship(
        'ElectionGroup',
        backref='roles',
        lazy='joined')

    # principal_id = schema.Column(
    #     UuidType,
    #     schema.ForeignKey('principal.id'),
    #     nullable=False)

    # principal = relationship(
    #     'Principal',
    #     back_populates='roles')

    # __table_args__ = (
    #     schema.UniqueConstraint('role', 'election_id', 'principal_id'),
    # )

    __mapper_args__ = {
        'polymorphic_identity': 'election-group-role',
    }


def get_principals_for(person_id, groups=[]):
    try:
        p = PersonPrincipal.query.filter(
            PersonPrincipal.person_id == person_id).one()
    except Exception:
        p = PersonPrincipal(person_id=person_id)
        PersonPrincipal.session.add(p)
    rg = []
    for grp in groups:
        try:
            rg.append(GroupPrincipal.query
                      .filter(GroupPrincipal.group_id == grp).one())
        except Exception:
            g = GroupPrincipal(group_id=grp)
            GroupPrincipal.session.add(g)
            rg.append(g)
    return p, rg


def list_roles():
    """ List all roles. """
    # return RoleList.query.all()
    pass


def get_role(role):
    """ Get role. """
    # return RoleList.query.filter(RoleList.role == role).one()
    pass


def get_principal(principal_id, cls=Principal):
    """ Get principal. """
    return cls.query.filter(
        cls.principal_id == principal_id).one()
