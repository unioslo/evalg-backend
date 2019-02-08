"""
Group operations.
"""
from sqlalchemy import func

from evalg.models.group import Group

# TODO:
#   Implement access control
#
# TODO:
#   Require database session to be passed in, rather than relying on a session
#   in Model.query


def search_group(filter_string):
    """ Look for groups that match a filter-string on one of
    the relevant attributes"""
    f = '%' + filter_string + '%'
    return Group.query.filter(func.lower(Group.name).like(f)).all()
