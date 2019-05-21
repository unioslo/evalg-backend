"""
evalg processes

These modules implements the evalg business logic layer.
"""
from . import count
from . import election
from . import group
from . import person
from . import pollbook
from . import role
from . import vote

__all__ = [
    'count',
    'election',
    'group',
    'person',
    'pollbook',
    'role',
    'vote',
]
