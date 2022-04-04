#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Representation of the currently logged in user.
"""
import datetime
import functools
import logging
from typing import Dict, List
import requests

from flask import current_app, request
from flask_feide_gk.utils import ContextAttribute
from flask_feide_gk.mock.gatekeeper import MockGatekeeperData
from sentry_sdk import capture_exception
from sqlalchemy.exc import IntegrityError

from evalg import db
from evalg.models.person import Person, PersonExternalId
from evalg.proc.group import (
    add_person_to_group,
    get_group_by_name,
    is_member_of_group,
    remove_person_from_group,
)
from evalg.utils import utcnow


logger = logging.getLogger(__name__)


class EvalgUser(object):
    MAX_PERSON_DATA_AGE = 60  # in minutes

    # map from Dataporten user info endpoint schema to Person model
    DP_ATTRIBUTE_MAP = {
        "name": "display_name",
        "email": "email",
    }

    # map from EvalgUser.ids to PersonExternalId.ID_TYPE_CHOICES
    ID_TYPE_MAP = {
        "feide": "feide_id",
        "nin": "nin",
        "dp_user_id": "feide_user_id",
    }

    _entitlement_mapping: Dict = {}
    _entitlement_groups: List = []

    gk_user = ContextAttribute("gk_user")
    feide_api = ContextAttribute("feide_api")
    _dp_user_info = ContextAttribute("dp_user_info")
    _get_dp_extended_user_info = ContextAttribute("feide_user_info")
    _person = ContextAttribute("person")
    _auth_finished = ContextAttribute("auth_finished")

    def init_app(self, app, gk_user, feide_api):
        @app.before_request
        def init_authentication():
            self.gk_user = gk_user
            if request.method == "OPTIONS":
                # If we are here, we have authenticated the Feide Gatekeeper,
                # but will not have been provided a user access token.
                return
            self.feide_api = feide_api
            self._auth_finished = False
            if self._person is None:
                person = self.find_or_create_person()
                if self.person_needs_update(person):
                    self.update_person(person)
                self._person = person
            logger.info(
                "Identified dp_user_id=%r as person_id=%r",
                self.dp_user_id,
                self._person.id,
            )
            self._auth_finished = True

    def get_dp_user_info(self):
        if self._dp_user_info is None:
            self._dp_user_info = self.feide_api.get_user_info().get("user")
        return self._dp_user_info

    def get_dp_extended_user_info(self):
        """Get the extended user info from the Dataporten API."""
        if self._get_dp_extended_user_info is None:
            try:
                self._get_dp_extended_user_info = (
                    self.feide_api.get_extended_user_info()
                )
            except requests.exceptions.HTTPError as e:
                # The extended user info api is currently not working for UiO
                # users. Capture the error so we do not brake the client.
                # The exception is captured by sentry.
                capture_exception(e)
                return None
        return self._get_dp_extended_user_info

    def find_or_create_person(self):
        person = self.find_person()
        if person is None:
            person = Person()
            try:
                self.update_person(person)
                logger.info("Creating a new person for dp_user_id=%r", self.dp_user_id)
            except IntegrityError as e:
                logger.warning("Could not create person. \n %r", e)
                db.session.rollback()
                person = self.find_person()
        return person

    def find_person(self):
        if (
            current_app.config["AUTH_METHOD"] == "feide"
            and not self.gk_user.access_token
        ):
            logger.warning("No access token in headers")
            return None
        matches = PersonExternalId.find_ids(*self.flattened_dp_ids).all()
        persons = set([x.person_id for x in matches])
        if not persons:
            return None
        elif len(persons) == 1:
            match = matches[0]
            person = Person.query.get(match.person_id)
            logger.info(
                "Found matching person_id=%r for dp_user_id=%r by id_type=%r",
                match.person_id,
                self.dp_user_id,
                match.id_type,
            )
        else:
            raise Exception("Matched multiple persons :-(")
        return person

    def is_authenticated(self):
        if self.gk_user:
            if isinstance(self.gk_user, MockGatekeeperData):
                return True
            elif self.gk_user.access_token:
                return True
        return False

    def is_authentication_finished(self):
        return bool(self.is_authenticated() and self._auth_finished)

    def update_person(self, person):
        self.update_person_data(person)
        self.update_person_ids(person)
        self.update_entitlement_groups(person)
        db.session.add(person)
        db.session.commit()

    def update_person_data(self, person):
        diff = []
        user_info = self.get_dp_user_info()
        for attr, value in user_info.items():
            if attr not in self.DP_ATTRIBUTE_MAP:
                continue
            destination = self.DP_ATTRIBUTE_MAP[attr]
            if getattr(person, destination, None) != value:
                diff.append(destination)
                setattr(person, destination, value)
        person.last_update_from_feide = utcnow()
        db.session.add(person)
        db.session.flush()
        if diff:
            logger.info("Updated fields %r for person_id=%r", diff, person.id)
        # TODO: use evalg.proc.person.update_person?

    def update_person_ids(self, person):
        logger.info("Updating identifiers for person_id=%r", person.id)
        existing_ids = set((x.id_type, x.id_value) for x in person.identifiers)
        dp_ids = set(list(self.flattened_dp_ids))
        to_remove = existing_ids.difference(dp_ids)
        to_add = dp_ids.difference(existing_ids)

        if to_remove:
            for id_obj in person.identifiers:
                if (id_obj.id_type, id_obj.id_value) in to_remove:
                    logger.info("Removing identifier=%r", id_obj)
                    person.identifiers.remove(id_obj)
        if to_add:
            for id_type, id_value in to_add:
                id_obj = PersonExternalId(
                    person_id=person.id,
                    id_type=id_type,
                    id_value=id_value,
                )
                logger.info("Adding identifier=%r", id_obj)
                person.identifiers.append(id_obj)
        db.session.flush()
        logger.info("Identifiers: %s", repr(person.identifiers))

    def _get_entitlement_groups(self):
        """Get all entitlement groups as defined in the config."""
        entitlement_groups = [
            get_group_by_name(db.session, x)
            for x in list(self._entitlement_mapping.keys())
        ]
        return {x.name: x for x in entitlement_groups if x is not None}

    def _get_persons_entitlement_group(self, person):
        """Get all entitlement groups a user is a member of."""
        return [
            x
            for x in list(self._entitlement_groups.values())
            if is_member_of_group(db.session, x, person)
        ]

    def _get_dp_entitlement_groups(self):
        """Get the users entitlement groups as defined in DP."""
        extended_user_data = self.get_dp_extended_user_info()
        dp_groups = []
        if extended_user_data and "eduPersonEntitlement" in extended_user_data:
            user_entitlements = extended_user_data["eduPersonEntitlement"]
            for group, entitlements in self._entitlement_mapping.items():
                if any(x in entitlements for x in user_entitlements):
                    dp_groups.append(self._entitlement_groups[group])
        return dp_groups

    def update_entitlement_groups(self, person):
        """Update entitlement_groups."""
        if not current_app.config["FEIDE_ENTITLEMENT_MAPPING_ENABLED"]:
            current_app.logger.info("Entitlements mapping not enabled," " skipping")
            return

        current_app.logger.info(
            "Updating person entitlements for " "person_id=%r", person.id
        )
        self._entitlement_mapping = current_app.config["FEIDE_ENTITLEMENT_MAPPING"]

        self._entitlement_groups = self._get_entitlement_groups()

        current_groups = self._get_persons_entitlement_group(person)
        dp_groups = self._get_dp_entitlement_groups()

        # Find groups to remove the user from
        current_groups_names = [x.name for x in current_groups]
        dp_groups_names = [x.name for x in dp_groups]
        to_remove = [x for x in current_groups if x.name not in dp_groups_names]

        # Find groups to add the user to
        to_add = [x for x in dp_groups if x.name not in current_groups_names]
        try:
            for group in to_remove:
                remove_person_from_group(db.session, group, person)
                current_app.logger.info(
                    "Removing user=%s from entitlement group=%s", person.id, group.name
                )
            for group in to_add:
                add_person_to_group(db.session, group, person)
                current_app.logger.info(
                    "Adding user=%s to entitlement group=%s", person.id, group.name
                )

            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.info(
                "Skipping entitlement groups, " "added by another request."
            )

    def person_needs_update(self, person):
        too_old = utcnow() - datetime.timedelta(minutes=self.MAX_PERSON_DATA_AGE)
        return (
            person.last_update_from_feide is None
            or person.last_update_from_feide < too_old
        )

    @property
    def person(self):
        if self._auth_finished:
            return self._person
        return None

    @property
    def dp_ids(self):
        return {
            "dp_user_id": (self.dp_user_id,),
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
