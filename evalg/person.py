#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Functional API for handling persons."""

from functools import wraps
from collections import defaultdict
from sqlalchemy import func, or_
from evalg import db
from .models.person import Person
from .api import NotFoundError
from .authorization import check_perms, all_perms, PermissionDenied


def perm(*permission):
    """Check perms function"""
    for perm in permission:
        assert perm in all_perms, '{} not valid'.format(permission)

    def fun(f):
        @wraps(f)
        def gun(*args, **kw):
            if 'principals' in kw:
                principals = kw['principals']
                del kw['principals']
            else:
                principals = ()
            if not check_perms(principals, permission):
                raise PermissionDenied()
            return f(*args, **kw)

        gun.is_protected = True
        return gun
    return fun


@perm('view-election', 'grant-role', 'upload-voters', 'vote-for', 'change-person')
def list_persons(**kw):
    return Person.query.filter_by(**kw)


def search_person(filter_string):
    """ Look for persons that match a filter-string on one of
    the relevant attributes"""
    filter_lc = filter_string.lower()
    split_filters = list(map(lambda f: '%' + f + '%', filter_lc.split(' ')))
    split_filters.append('%' + filter_lc + '%')
    return Person.query.filter(
        or_(*[func.lower(Person.display_name).like(f) for f in split_filters])).all()
#        |
#        func.lower(Person.username).like(filter_lc) |
#        func.lower(Person.nin).like(filter_lc)).all()


@perm('change-person')
def make_person(**args):
    return Person(**args)


def get_person(person_id):
    person = Person.query.get(person_id)
    if person is None:
        raise NotFoundError(
            details="No such person with id={uuid}".format(
                uuid=person_id))
    return person


def _update_person(person, kwargs):
    if 'external_id' in kwargs:
        ext = kwargs['external_id']
        del kwargs['external_id']
        current = defaultdict(set)
        map(lambda x: current[x.id_type].add(x.external_id),
            person.external_ids)
        for k, value in ext.items():
            if value not in current[k]:
                person.external_ids.append(PersonExternalId(id_type=k,
                                                            external_id=value))
    for k, v in kwargs.items():
        if hasattr(person, k) and getattr(person, k) != v:
            setattr(person, k, v)
    return person


@perm('change-person')
def update_person(person, **updates):
    return _update_person(person, updates)


def update_self(person, **updates):
    """Called during login to update self from external sources."""
    return _update_person(person, updates)


@perm('change-person')
def delete_person(person):
    db.session.delete(person)
