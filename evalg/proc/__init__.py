"""
evalg processes

These modules implements the evalg business logic layer.
"""
from . import group
from . import count
from . import pollbook
from . import vote


__all__ = [
    'count',
    'group',
    'pollbook',
    'vote',
]
