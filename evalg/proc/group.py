"""
Group operations.
"""
from sqlalchemy import func
from sqlalchemy import exists
from sqlalchemy import and_

from evalg.models.group import Group, GroupMembership


def search_groups(session, filter_string):
    """ Look for groups that match a filter-string on one of
    the relevant attributes"""
    f = '%' + filter_string + '%'
    return session.query(Group).filter(func.lower(Group.name).like(f))


def is_member_of_group(session, group, person):
    """Check if person is a member of a group."""
    return session.query(exists().where(and_(
        GroupMembership.group_id == group.id,
        GroupMembership.person_id == person.id))
    ).scalar()
