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

from sqlalchemy import UniqueConstraint
from sqlalchemy import types
from sqlalchemy.sql import schema
from sqlalchemy.orm import relationship

from evalg.database.types import JsonType
from evalg.database.types import UuidType
from .base import ModelBase


class Principal(ModelBase):
    """
    Security principal.

    An evalg security principal is an abstract representation of an individual
    user or a group of users.
    """

    __tablename__ = 'principal'
    __versioned__ = {}

    principal_id = schema.Column(
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

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.principal_id'),
        default=uuid.uuid4,
        primary_key=True)

    person_id = schema.Column(
        UuidType,
        schema.ForeignKey('person.id'),
        nullable=False)

    person = relationship(
        'Person',
        back_populates='principals')

    __mapper_args__ = {
        'polymorphic_identity': 'person-principal',
        'inherit_condition': principal_id == Principal.principal_id,
    }


class GroupPrincipal(Principal):
    """ Security principal based on membership in a group. """

    __tablename__ = 'group_principal'
    __versioned__ = {}

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.principal_id'),
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
        'inherit_condition': principal_id == Principal.principal_id,
    }


class RolePermission(ModelBase):
    """ Permissions granted by role. """

    __tablename__ = 'role_permission'
    __versioned__ = {}

    code = schema.Column(
        types.String,
        schema.ForeignKey('permission.code'),
        primary_key=True)

    role = schema.Column(
        types.String,
        schema.ForeignKey('role_list.role'),
        primary_key=True)


class Role(ModelBase):
    """ Roles granted to a principal. """

    __tablename__ = 'role'
    __versioned__ = {}

    grant_id = schema.Column(
        UuidType,
        default=uuid.uuid4,
        primary_key=True)

    role = schema.Column(
        types.String,
        schema.ForeignKey('role_list.role'),
        nullable=False)

    role_type = schema.Column(
        types.String(50),
        nullable=False)

    trait = relationship(
        'RoleList',
        foreign_keys=(role, role_type))

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.principal_id'),
        nullable=False)

    principal = relationship(
        'Principal',
        back_populates='roles')

    __mapper_args__ = {
        'polymorphic_identity': 'role',
        'polymorphic_on': role_type
    }

    def supports(self, perm, **kw):
        return perm in (x.code for x in self.trait.perms)


class RoleList(ModelBase):
    """ List of roles in system. """

    __tablename__ = 'role_list'
    __versioned__ = {}

    role = schema.Column(
        types.String,
        primary_key=True)

    role_type = schema.Column(
        types.String(50),
        nullable=False)

    role_class = Role

    name = schema.Column(
        JsonType,
        nullable=False)

    perms = relationship(
        'Permission',
        secondary=RolePermission.__table__,
        back_populates='roles')

    __mapper_args__ = {
        'polymorphic_identity': 'role-list',
        'polymorphic_on': role_type
    }

    def makerole(self, **kw):
        """Get a matching role."""
        return self.role_class(trait=self, **kw)


class OuRole(Role):
    """ Roles granted to principal on OU. """

    __tablename__ = 'ou_role'
    __versioned__ = {}

    grant_id = schema.Column(
        UuidType,
        schema.ForeignKey('role.grant_id'),
        default=uuid.uuid4,
        primary_key=True)

    role = schema.Column(
        types.String,
        schema.ForeignKey('ou_role_list.role'),
        nullable=False)

    ou_id = schema.Column(
        UuidType,
        schema.ForeignKey('organizational_unit.id'),
        nullable=False)

    ou = relationship('OrganizationalUnit')

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.principal_id'),
        nullable=False)

    principal = relationship(
        'Principal',
        back_populates='roles')

    __table_args__ = (
        UniqueConstraint('role', 'ou_id', 'principal_id'),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'ou-role',
    }

    def supports(self, perm, ou=None, **kw):
        if ou is None:
            return False
        if self.ou > ou:
            return False
        return super().supports(perm, **kw)


class OuRoleList(RoleList):
    """ Roles based on OU. """

    __tablename__ = 'ou_role_list'
    __versioned__ = {}

    role = schema.Column(
        types.String,
        schema.ForeignKey('role_list.role'),
        primary_key=True)

    role_class = OuRole

    __mapper_args__ = {
        'polymorphic_identity': 'ou-role-list',
        'inherit_condition': role == RoleList.role,
    }


class ElectionRole(Role):
    """ Roles granted on election. """

    __tablename__ = 'election_role'
    __versioned__ = {}

    grant_id = schema.Column(
        UuidType,
        schema.ForeignKey('role.grant_id'),
        default=uuid.uuid4,
        primary_key=True)

    role = schema.Column(
        types.String,
        schema.ForeignKey('election_role_list.role'),
        nullable=False)

    election_id = schema.Column(
        UuidType,
        schema.ForeignKey('election.id'),
        nullable=False)

    election = relationship(
        'Election',
        backref='roles',
        lazy='joined')

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.principal_id'),
        nullable=False)

    principal = relationship(
        'Principal',
        back_populates='roles')

    __table_args__ = (
        UniqueConstraint('role', 'election_id', 'principal_id'),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'election-role',
    }

    def supports(self, perm, election_id=None, **kw):
        if election_id != self.election_id:
            return False
        return super().supports(perm, **kw)


class ElectionRoleList(RoleList):
    """ Roles given on election (group). """

    __tablename__ = 'election_role_list'
    __versioned__ = {}

    role = schema.Column(
        types.String,
        schema.ForeignKey('role_list.role'),
        primary_key=True)

    role_class = ElectionRole

    __mapper_args__ = {
        'polymorphic_identity': 'election-role-list',
        'inherit_condition': role == RoleList.role,
    }

    def makerole(self, **kw):
        """Override to handle group role vs. election roles."""
        return (ElectionGroupRole if 'group_id' in kw
                else self.role_class)(trait=self, **kw)


class ElectionGroupRole(Role):
    """ Roles granted on election. """

    __tablename__ = 'election_group_role'
    __versioned__ = {}

    grant_id = schema.Column(
        UuidType,
        schema.ForeignKey('role.grant_id'),
        default=uuid.uuid4,
        primary_key=True)

    role = schema.Column(
        types.String,
        schema.ForeignKey('election_role_list.role'),
        nullable=False)

    group_id = schema.Column(
        UuidType,
        schema.ForeignKey('election_group.id'))

    group = relationship(
        'ElectionGroup',
        backref='roles',
        lazy='joined')

    principal_id = schema.Column(
        UuidType,
        schema.ForeignKey('principal.principal_id'),
        nullable=False)

    principal = relationship(
        'Principal',
        back_populates='roles')

    __table_args__ = (
        UniqueConstraint('role', 'group_id', 'principal_id'),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'election-group-role',
    }

    def supports(self, perm, group_id=None, **kw):
        if group_id != self.group_id:
            return False
        return super().supports(perm, **kw)


class Permission(ModelBase):
    """Permission."""

    __tablename__ = 'permission'
    __versioned__ = {}

    code = schema.Column(
        types.String,
        primary_key=True)

    doc = schema.Column(types.String)

    roles = relationship(
        'RoleList',
        secondary=RolePermission.__table__,
        back_populates='perms')


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
    return RoleList.query.all()


def get_role(role):
    """ Get role. """
    return RoleList.query.filter(RoleList.role == role).one()


def get_principal(principal_id, cls=Principal):
    """ Get principal. """
    return cls.query.filter(
        cls.principal_id == principal_id).one()
