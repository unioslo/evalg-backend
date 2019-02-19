"""
Custom SQLAlchemy column types.

All types should produce an executable ``repr()``, for compatibility
with alembic.
"""
import datetime

import flask.json
import sqlalchemy.types
import sqlalchemy.util
import sqlalchemy_utils
import sqlalchemy_utils.types.json
from sqlalchemy_json import MutableJson
from sqlalchemy_json import NestedMutableJson


# Monkey patch sqlalchemy_utils serializer.  Note that sqlalchemy_json inherits
# from the data type from sqlalchemy_utils - so setting serializer there takes
# care of both instances.
#
# TODO:
# 1. This patching should maybe be done differently -- maybe override the
#    JsonType-method for serializing to the db?
# 2. We might want to implement our own Json serializer to deal with custom
#    data types. The flask one simply extends the stdlib json module with
#    support for serializing datetime.datatime and uuid.UUID
# 3. Note that JsonType only use the json-implementation for serializing to
#    json-strings for all db-engines *but* postgres -- if using postgres, json
#    serialization is delegated to the engine, so we'll have to make sure to
#    use the same serializer there...
sqlalchemy_utils.types.json.json = flask.json


class UrlType(sqlalchemy_utils.URLType):
    """ Column type for URLs. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


class IpAddressType(sqlalchemy_utils.types.ip_address.IPAddressType):
    """ Column type for ip addresses. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


class UuidType(sqlalchemy_utils.UUIDType):
    """ Column type for UUIDs. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


class JsonType(sqlalchemy_utils.types.json.JSONType):
    """ Column type for JSON data. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


class UtcDateTime(sqlalchemy.types.TypeDecorator):
    """
    A DateTime type that normalizes all datetimes to UTC.

    The object ensures that:
        - datetime objects added to the database are converted to utc
        - no naive datetimes are written to the database
    """

    impl = sqlalchemy.types.DateTime

    def __init__(self):
        super(UtcDateTime, self).__init__(timezone=True)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not value.tzinfo:
            # We refuse to add datetimes without timezone info.  If the
            # datetime is UTC, it should be explicitly marked with tzinfo.
            raise ValueError("UtcDateTime got a naive datetime object")
        return value.astimezone(datetime.timezone.utc)

    def process_result_value(self, value, dialect):
        """ normalize datetimes to the python3 builtin utc tz. """
        if value is not None:
            value = value.astimezone(datetime.timezone.utc)
        return value

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


__all__ = [
    'JsonType',
    'MutableJson',
    'NestedMutableJson',
    'UrlType',
    'UuidType',
]
