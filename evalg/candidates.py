# -*- coding: utf-8 -*-

""" Business logic for candidates. """


from functools import singledispatch, wraps
from evalg import db
# from .authorization import check_perms, all_perms, PermissionDenied
from .metadata import eperm
from .models.candidate import Candidate
from .models.election import Election
from .models.election_list import ElectionList


class NotFoundError(Exception):
    pass


# def lperm(arg=0, *permission):
#     """Check perms function for election"""
#     for perm in permission:
#         assert perm in all_perms
#     if isinstance(arg, int):
#         def election(args, kw):
#             return args[arg]
#     else:
#         def election(args, kw):
#             return kw[arg]

#     def fun(f):
#         @wraps(f)
#         def gun(principals=None, *args, **kw):
#             e = election(args, kw)
#             if not check_perms(principals, permission, election=e, ou=e.ou):
#                 raise PermissionDenied()
#             return f(*args, **kw)

#         gun.is_protected = True
#         return gun
#     return fun


# def cperm(arg=0, *permission):
#     """Check perms function for election"""
#     for perm in permission:
#         assert perm in all_perms
#     if isinstance(arg, int):
#         def election(args, kw):
#             c = args[arg]
#             if isinstance(c, Candidate):
#                 return c.election
#             return c.candidate.election
#     else:
#         def election(args, kw):
#             c = kw[arg]
#             if isinstance(c, Candidate):
#                 return c.list.election
#             return c.candidate.list.election

#     def fun(f):
#         @wraps(f)
#         def gun(principals=None, *args, **kw):
#             e = election(args, kw)
#             if not check_perms(principals, permission, election=e, ou=e.ou):
#                 raise PermissionDenied()
#             return f(*args, **kw)

#         gun.is_protected = True
#         return gun
#     return fun


# def rcperm(*permission):
#     """Check perms function for election"""
#     for perm in permission:
#         assert perm in all_perms

#     def election(c):
#         if isinstance(c, Candidate):
#             return c.list.election
#         return c.candidate.election

#     def fun(f):
#         @wraps(f)
#         def gun(principals=None, *args, **kw):
#             ret = f(*args, **kw)
#             e = election(ret)
#             if not check_perms(principals, permission, election=e, ou=e.ou):
#                 raise PermissionDenied()
#             return ret

#         gun.is_protected = True
#         return gun
#     return fun


def get_lists(election):
    """ List election's candidate lists. """
    return election.lists


def get_list(list_id):
    """ Return a candidate list. """
    l = ElectionList.query.get(list_id)
    if l is None:
        raise NotFoundError(
            details="No such candidate list with id={uuid}".format(
                uuid=list_id))
    return l


# @eperm('change-candidates')
def make_list(election, **args):
    """ Make a new list. """
    return ElectionList(election=election, **args)


@singledispatch
def get_candidates(obj, **kw):
    """ List obj's candidates. """


@get_candidates.register(Election)
# @eperm('view-election')
def get_election_candidates(election):
    """ Accumulate all election's lists' candidates. """
    return election.lists[0].candidates


@get_candidates.register(ElectionList)
# @lperm('view-election')
def get_list_candidates(lst):
    """ Return candidates. """
    return lst.candidates


@singledispatch
def update(obj, **kw):
    """Update obj"""


@update.register(ElectionList)
# @lperm('change-candidates')
def update_list(lst, **kw):
    for k, v in kw.items():
        setattr(lst, k, v)


@update.register(Candidate)
def update_candidate(cand, **kw):
    for k, v in kw.items():
        setattr(cand, k, v)


# @rcperm('change-candidates')
def make_candidate(**args):
    c = Candidate(**args)
    db.session.add(c)
    db.session.commit()
    return c


def get_candidate(candidate_id):
    """ Get candidate. """
    candidate = Candidate.query.get(candidate_id)
    if candidate is None:
        raise NotFoundError(
            details="No such candidate with id={uuid}".format(
                uuid=candidate_id)
        )
    return candidate
