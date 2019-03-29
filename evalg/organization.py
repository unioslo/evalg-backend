#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Functional API for handling organization units."""

from functools import wraps
from .models.ou import OrganizationalUnit
from .authorization import check_perms, all_perms, PermissionDenied

class NotFoundError(Exception):
    pass


def ouperm(permission, arg=0):
    """Check perms function for ou"""
    assert permission in all_perms, '{} not valid'.format(permission)
    if isinstance(arg, int):
        def ou(args, kw):
            return args[arg]
    else:
        def ou(args, kw):
            return kw[arg]

    def fun(f):
        @wraps(f)
        def gun(*args, **kw):
            if 'principals' in kw:
                principals = kw['principals']
                del kw['principals']
            else:
                principals = ()
            o = ou(args, kw)
            if not check_perms(principals, permission, ou=o):
                raise PermissionDenied()
            return f(*args, **kw)

        gun.is_protected = True
        return gun
    return fun


def rperm(*permission):
    """Check if user has perms on return value. """
    for perm in permission:
        assert perm in all_perms

    def fun(f):
        @wraps(f)
        def gun(*args, **kw):
            if 'principals' in kw:
                principals = kw['principals']
                del kw['principals']
            else:
                principals = ()
            ret = f(*args, **kw)
            if ret is not None:
                if not check_perms(principals, permission, ou=ret):
                    raise PermissionDenied()
            return ret
        gun.is_protected = True
        return gun
    return fun


def get_ou(ou_id):
    """ Get Ou """
    ou = OrganizationalUnit.query.get(ou_id)
    if ou is None or ou.deleted:
        raise NotFoundError(
            details="No such organizational unit with id={uuid}".format(
                uuid=ou_id))
    return ou


def list_ous():
    """ List OUs. """
    return list(filter(lambda x: not x.deleted, OrganizationalUnit.query.all()))


@ouperm('change-ou')
def update_ou(ou, **args):
    """ Update OU. """
    for k, v in args:
        if hasattr(ou, k) and getattr(ou, k) != v:
            setattr(ou, k, v)
    return ou


@rperm('change-ou')
def make_ou(**args):
    """ Create new ou. """
    return OrganizationalUnit(**args)
