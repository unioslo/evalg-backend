""" Custom graphql type mappings. """

import datetime
import logging

import aniso8601
import pytz
from graphene.types import Scalar
from graphql.language import ast


logger = logging.getLogger(__name__)


# TODO: This is a temporary hack -- we should only accept datetimes *with*
# timezone data.
default_timezone = pytz.timezone('Europe/Oslo')


def _parse_date(datestr):
    """ Parse an ISO8601 date value. """
    try:
        # TODO: Temporary hack -- accept datetime strings
        # We should require clients to send an ISO8601 date, without time or
        # timezone data.
        date = _parse_datetime(datestr).date()
        logger.warning('got datetime (%s), expected date', repr(datestr))
    except ValueError:
        date = aniso8601.parse_date(datestr)
    return date


def _parse_datetime(datestr):
    # Allow use of space as separator
    for parse in (
        lambda d: aniso8601.parse_datetime(d, delimiter='T'),
        lambda d: aniso8601.parse_datetime(d, delimiter=' '),
    ):
        try:
            date = parse(datestr)
            break
        except ValueError:
            continue
    else:
        # for-loop completed
        raise ValueError("invalid datetime %r" % (datestr, ))

    if not date.tzinfo:
        # TODO: Temporary hack -- apply timezone
        # We should require all clients to include timezone
        logger.warning('got datetime without timezone (%s), assuming %s',
                       repr(datestr), str(default_timezone))
        date = default_timezone.localize(date)
    return date


class Date(Scalar):
    """ A date type """

    @staticmethod
    def serialize(dt):
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        return dt.isoformat()

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.StringValue):
            return _parse_date(node.value)

    @staticmethod
    def parse_value(value):
        return _parse_date(value)


class DateTime(Scalar):
    """ A datetime type. """

    @staticmethod
    def serialize(dt):
        return dt.isoformat()

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.StringValue):
            return _parse_datetime(node.value)

    @staticmethod
    def parse_value(value):
        return _parse_datetime(value)
