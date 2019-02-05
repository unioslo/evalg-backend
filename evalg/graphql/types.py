""" Custom graphql type mappings. """

import datetime
import logging

import aniso8601
from graphene.types import Scalar
from graphql.language import ast


logger = logging.getLogger(__name__)


def _parse_date(datestr):
    """ Parse an ISO8601 date value. """
    return aniso8601.parse_date(datestr)


def _parse_datetime(datestr):
    """
    Parse an ISO8601 datetime value, and require timezone.

    The date and time separator may be 'T' or ' '.
    """
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
        # for-loop completed without successful `parse()`
        raise ValueError("invalid datetime %r" % (datestr, ))

    if not date.tzinfo:
        raise ValueError("missing timezone in datetime %r" % (datestr, ))
    return date


class Date(Scalar):
    """ A graphql ISO8601 date type. """

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
    """ A graphql ISO8601 datetime type. """

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
