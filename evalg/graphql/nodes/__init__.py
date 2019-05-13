"""
GraphQL object models.

Each of these submodules implements one or more ObjectTypes, as well as
resolvers and mutations.
"""

from . import base
from . import candidates
from . import election
from . import election_group
from . import election_group_count
from . import election_result
from . import group
from . import person
from . import pollbook
from . import roles
from . import votes

__all__ = [
    'base',
    'candidates',
    'election',
    'election_group',
    'election_group_count',
    'election_result',
    'group',
    'person',
    'pollbook',
    'roles',
    'votes',
]
