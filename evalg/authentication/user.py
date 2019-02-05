#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Representation of the currently logged in user.
"""
import datetime
import functools
import logging

from flask import g, current_app
from flask_feide_gk.utils import ContextAttribute

from evalg import db
from evalg.models.person import Person, PersonExternalId
from evalg.utils import utcnow


logger = logging.getLogger(__name__)

class EvalgUser(object):
    MAX_PERSON_DATA_AGE = 60  # in minutes

    # map from Feide LDAP schema to Person model
    FEIDE_ATTRIBUTE_MAP = {
        'givenName': 'first_name',
        'sn': 'last_name',
        'displayName': 'display_name',
        'mail': 'email',
    }

    # map from EvalgUser.ids to PersonExternalId.ID_TYPE_CHOICES
    ID_TYPE_MAP = {
        'feide': 'feide_id',
        'nin': 'nin',
        'dp_user_id': 'dp_user_id',
    }

    gk_user = ContextAttribute('gk_user')
    feide_api = ContextAttribute('feide_api')
    _feide_user_info = ContextAttribute('feide_user_info')
    _person = ContextAttribute('person')

    def init_app(self, app, gk_user, feide_api):
        @app.before_request
        def init_authentication():
            self.gk_user = gk_user
            self.feide_api = feide_api

    def get_feide_user_info(self):
        if self._feide_user_info is None:
            self._feide_user_info = self.feide_api.get_user_info()
        return self._feide_user_info

    def find_person(self):
        matches = PersonExternalId.find_ids(*self.flattened_dp_ids).all()
        persons = set([x.person_id for x in matches])
        if not persons:
            # We create a new person
            logger.info('Creating a new person for dp_user_id=%r',
                        self.dp_user_id)
            person = Person()
            self.update_person(person)
        elif len(persons) == 1:
            match = matches[0]
            person = Person.query.get(match.person_id)
            logger.info(
                'Found matching person_id=%r for dp_user_id=%r by id_type=%r',
                match.person_id,
                self.dp_user_id,
                match.id_type)
        else:
            # TODO: we're in deep shit
            raise Exception('Matched multiple persons :-(')
        return person

    def update_person(self, person):
        self.update_person_data(person)
        self.update_person_ids(person)
        db.session.add(person)
        db.session.commit()

    def update_person_data(self, person):
        diff = []
        for attr, value in self.get_feide_user_info().items():
            if attr not in self.FEIDE_ATTRIBUTE_MAP:
                continue
            destination = self.FEIDE_ATTRIBUTE_MAP[attr]
            if getattr(person, destination, None) != value:
                diff.append(destination)
                setattr(person, destination, value)
        person.last_update_from_feide = utcnow()
        db.session.add(person)
        db.session.flush()
        if diff:
            logger.info('Updated fields %r for person_id=%r',
                        diff, person.id)
        # TODO: use evalg.person._update_person?

    def update_person_ids(self, person):
        logger.info('person.id %r', person.id)
        keep = list()
        remove = list()
        existing_ids = set([(x.id_type, x.external_id) for x in person.external_ids])
        dp_ids = set(list(self.flattened_dp_ids))
        to_remove = existing_ids.difference(dp_ids)
        to_add = dp_ids.difference(existing_ids)
        if to_remove:
            for existing_id in person.external_ids:
                if (existing_id.id_type, existing_id.external_id) in to_remove:
                    logger.info('Deleting external ID: %r', existing_id)
                    person.external_ids.remove(existing_id)
        if to_add:
            for id_type, value in to_add:
                new_id = PersonExternalId(
                    person_id=person.id,
                    id_type=id_type,
                    external_id=value,
                )
                logger.info('Adding new external ID: %r', new_id)
                person.external_ids.append(new_id)
        db.session.flush()
        logger.info(repr(person.external_ids))

    def set_person(self, person):
        too_old = utcnow() - datetime.timedelta(minutes=self.MAX_PERSON_DATA_AGE)
        if (person.last_update_from_feide is None or
            person.last_update_from_feide < too_old):
            self.update_person(person)
        self._person = person
        current_app.logger.info('Identified dp_user_id=%r as person_id=%r',
                    self.dp_user_id,
                    self.person.id)

    @property
    def person(self):
        if self._person is None:
            # TODO: try/except
            self.set_person(self.find_person())
        return self._person

    @property
    def dp_ids(self):
        return {
            'dp_user_id': (self.dp_user_id, ),
            **self.dp_user_sec,
        }

    @property
    def flattened_dp_ids(self):
        for id_type in self.dp_ids:
            if id_type not in self.ID_TYPE_MAP:
                continue
            for value in self.dp_ids[id_type]:
                yield self.ID_TYPE_MAP[id_type], value

    @property
    def dp_user_id(self):
        return self.gk_user.user_id

    @property
    def dp_user_sec(self):
        return self.gk_user.user_sec

    def require(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: require something here?
            return func(*args, **kwargs)
        return wrapper
