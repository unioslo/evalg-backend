"""
Custom SQLAlchemy column types.

All types should produce an executable ``repr()``, for compatibility
with alembic.
"""

import flask.json
import sqlalchemy.util
import sqlalchemy_utils
import sqlalchemy_utils.types.json

from graphene.types.generic import GenericScalar
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphene_sqlalchemy.converter import convert_column_to_string
from graphene_sqlalchemy.converter import convert_json_to_string
from graphene_sqlalchemy.converter import get_column_doc
from graphene_sqlalchemy.converter import is_column_nullable
from sqlalchemy_json import MutableJson
from sqlalchemy_json import NestedMutableJson


# Monkey patch sqlalchemy_json serializer
sqlalchemy_utils.types.json.json = flask.json


class UrlType(sqlalchemy_utils.URLType):
    """ Column type for URLs. """

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


class IpAddressType(sqlalchemy_utils.types.ip_address.IPAddressType):
    """ Column type for ip addresses. """

    def __repr__(self):
        return sqlalchemy.util.generic_repr(self)


@convert_sqlalchemy_type.register(JsonType)
@convert_sqlalchemy_type.register(MutableJson)
@convert_sqlalchemy_type.register(NestedMutableJson)
def convert_json_to_generic_scalar(type, column, registry=None):
    return GenericScalar(
        description=get_column_doc(column),
        required=not(is_column_nullable(column)))


# Graphene compatibility:
convert_sqlalchemy_type.register(UrlType)(convert_column_to_string)
convert_sqlalchemy_type.register(UuidType)(convert_column_to_string)


__all__ = [
    'JsonType',
    'MutableJson',
    'NestedMutableJson',
    'UrlType',
    'UuidType',
]
