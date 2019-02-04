"""
All evalg graphql mutations
"""
from .election import ElectionMutations


class Mutations(
    ElectionMutations,
):
    """ election mutations collection class. """
    pass


__all__ = [
    'Mutations',
    'ElectionMutations',
]
