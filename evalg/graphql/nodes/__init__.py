"""
GraphQL object models.

Each of these submodules implements one or more ObjectTypes, as well as
resolvers and mutations.
"""

from . import election_group
from . import election
from . import pollbook
from . import candidates
from . import person
from . import group
from . import roles


__all__ = [
    'election_group',
    'election',
    'pollbook',
    'candidates',
    'person',
    'group',
    'roles',
]
