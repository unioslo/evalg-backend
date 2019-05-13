#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module implements person maintenance.
"""

from collections import defaultdict
from sqlalchemy import func, or_

from evalg.models.person import Person, PersonExternalId


def search_persons(session, filter_string):
    """ Search for persons by a string. """
    filter_lc = filter_string.lower()
    split_filters = list(map(lambda f: '%' + f + '%', filter_lc.split(' ')))
    split_filters.append('%' + filter_lc + '%')
    # TODO: search for username? nin?
    return session.query(Person).filter(
        or_(
            *[func.lower(Person.display_name).like(f) for f in split_filters]
        )
    )


def update_person(person, kwargs):
    identifiers = kwargs.pop('identifiers', {})
    if identifiers:
        current = defaultdict(set)
        map(lambda x: current[x.id_type].add(x.id_value),
            person.identifiers)
        for k, value in identifiers.items():
            if value not in current[k]:
                person.identifiers.append(
                    PersonExternalId(id_type=k, id_value=value))
    for k, v in kwargs.items():
        if hasattr(person, k) and getattr(person, k) != v:
            setattr(person, k, v)
    return person
