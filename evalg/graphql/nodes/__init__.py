"""
GraphQL object models.

Each of these submodules implements one or more ObjectTypes, as well as
resolvers and mutations.
"""

from . import candidates
from . import election
from . import election_group
from . import group
from . import person
from . import pollbook
from . import privkeys_backup
from . import roles
from . import votes

__all__ = [
    'candidates',
    'election',
    'election_group',
    'group',
    'person',
    'pollbook',
    'privkeys_backup',
    'roles',
    'votes',
]
