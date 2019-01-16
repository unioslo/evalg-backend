"""
Custom SQLAlchemy column types.

All types should produce an executable ``repr()``, for compatibility
with alembic.
"""

import flask.json
import sqlalchemy.util
import sqlalchemy_utils
import sqlalchemy_utils.types.json
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphene_sqlalchemy.converter import convert_column_to_string
from graphene_sqlalchemy.converter import convert_json_to_string
from sqlalchemy_json import MutableJson
from sqlalchemy_json import NestedMutableJson


# Monkey patch sqlalchemy_json serializer
sqlalchemy_utils.types.json.json = flask.json


class URLType(sqlalchemy_utils.URLType):
    """ Column type for URLs. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


class UUIDType(sqlalchemy_utils.UUIDType):
    """ Column type for UUIDs. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


class JSONType(sqlalchemy_utils.types.json.JSONType):
    """ Column type for JSON data. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


# Graphene compatibility:

convert_sqlalchemy_type.register(URLType)(convert_column_to_string)
convert_sqlalchemy_type.register(UUIDType)(convert_column_to_string)
convert_sqlalchemy_type.register(JSONType)(convert_json_to_string)


__all__ = [
    'JSONType',
    'MutableJson',
    'NestedMutableJson',
    'URLType',
    'UUIDType',
]
