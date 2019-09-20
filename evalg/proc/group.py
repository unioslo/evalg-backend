"""
Group operations.
"""
from sqlalchemy import func
from sqlalchemy import exists
from sqlalchemy import and_

import evalg

from evalg.models.group import Group, GroupMembership

from sqlalchemy_continuum import version_class


def search_groups(session, filter_string):
    """ Look for groups that match a filter-string on one of
    the relevant attributes"""
    f = '%' + filter_string + '%'
    return session.query(Group).filter(func.lower(Group.name).like(f))


def get_group_by_name(session, group_name):
    """Get a group by it's name."""
    return session.query(Group).filter(Group.name == group_name).first()


def get_group_by_id(session, group_id):
    """Get a group by it's id."""
    return session.query(Group).filter(Group.id == group_id).first()


def is_member_of_group(session, group, person):
    """Check if person is a member of a group."""
    return session.query(exists().where(and_(
        GroupMembership.group_id == group.id,
        GroupMembership.person_id == person.id))
    ).scalar()


def add_person_to_group(session, group, person):
    """Add a person to a group."""
    membership = evalg.database.query.get_or_create(
        session,
        GroupMembership,
        group_id=group.id,
        person_id=person.id,
    )
    session.add(membership)
    session.flush()
    return membership


def remove_person_from_group(session, group, person):
    """Remove a person from a group."""
    membership = session.query(GroupMembership).filter(and_(
        GroupMembership.group_id == group.id,
        GroupMembership.person_id == person.id)).first()
    if membership:
        session.delete(membership)
        session.flush()


def get_user_groups(session, person):
    """Get the groups a user is a member of."""
    memberships = session.query(GroupMembership).filter(
        GroupMembership.person_id == person.id).all()
    return [get_group_by_id(session, x.group_id) for x in memberships]


def get_election_key_meta(session, election_group_id):
    ElectionGroupVersion = version_class(evalg.models.election.ElectionGroup)
    return session.query(ElectionGroupVersion).filter(
        ElectionGroupVersion.id == election_group_id,
        ElectionGroupVersion.public_key_mod).order_by(
        ElectionGroupVersion.transaction_id.desc()).limit(1).all()
