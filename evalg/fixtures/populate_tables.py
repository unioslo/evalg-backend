#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helper that populates tables with example data.

TODO: Replace use of flask_fixtures with something else. Preferably something
that decodes string input like datetime values on-demand (i.e. when the
database field is a Date, Datetime or UtcDateTime field...)
"""
import datetime
import logging
import json
import time

import aniso8601
import flask_fixtures
import flask_fixtures.loaders
import pytz
from flask import current_app

from evalg import db


default_timezone = pytz.timezone('Europe/Oslo')
logger = logging.getLogger(__name__)


def parse_date(value):
    """
    Parse date values, e.g. 1990-11-27.

    Note: we don't want to allow all ISO8601 date values here, as that would
    make e.g. "1" a valid date.
    """
    date_st = time.strptime(value, '%Y-%m-%d')[0:3]
    return datetime.date(*date_st)


def parse_datetime(value):
    """
    Parse datetime values, e.g. "1990-11-27 13:37:00".

    Here we strictly support ISO8601 datetimes, with or without timezones.
    If no timezone is given, we assume a default "Europe/Oslo" timezone.
    """
    for parse in (
            lambda d: aniso8601.parse_datetime(d, delimiter='T'),
            lambda d: aniso8601.parse_datetime(d, delimiter=' ')):
        try:
            dt = parse(value)
            break
        except ValueError:
            continue
    else:
        # for-loop completed w/o successful parse_datetime
        raise ValueError("Invalid datetime %r" % (value, ))

    # We allow fixture datetime with missing timezone -- we just assume
    # naive datetimes are supposed to be in default_timezone.
    if not dt.tzinfo:
        dt = default_timezone.localize(dt)
    return dt


class JsonLoader(flask_fixtures.loaders.FixtureLoader):

    extensions = ('.json', '.js')

    def load(self, filename):

        obj_parsers = (parse_datetime, parse_date)

        def _datetime_hook(dct):
            for key, value in list(dct.items()):
                for parse in obj_parsers:
                    try:
                        dct[key] = parse(value)
                        logger.debug('key=%s valid with parser=%s (%r)',
                                     key, parse.__name__, value)
                        break
                    except Exception:
                        continue
            return dct

        with open(filename) as fin:
            logger.info("processing json file %r", filename)
            return json.load(fin, object_hook=_datetime_hook)


# Monkey patch the flask_fixtures json-loader, so that we're sure that only our
# implmentation applies to json files.
flask_fixtures.loaders.JSONLoader.extensions = tuple()


class Populator(flask_fixtures.FixturesMixin):
    fixtures = [
        'ous.json',
        'elections.json',
        'election_lists.json',
        'candidates.json',
        'pollbooks.json',
        'persons.json',
        'groups.json',
        'voters.json',
        'authz.json',
    ]

    app = current_app
    db = db
