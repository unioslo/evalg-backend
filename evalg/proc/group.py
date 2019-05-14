"""
Group operations.
"""
from sqlalchemy import func

from evalg.models.group import Group

# TODO:
#   Implement access control
#


def search_groups(session, filter_string):
    """ Look for groups that match a filter-string on one of
    the relevant attributes"""
    f = '%' + filter_string + '%'
    return session.query(Group).filter(func.lower(Group.name).like(f))
