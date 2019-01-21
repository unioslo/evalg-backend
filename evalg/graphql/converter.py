"""
Custom evalg graphene conversions.

This module specifies the SQLAlchemy to graphene data types for non-default
sqlalchemy/graphene data types.

The conversions must be specified before the relevant field name is used e.g.
in models and migrations.

This file must contain conversions for any type used in
py:mod`evalg.database.types`.
"""
from graphene.types.generic import GenericScalar
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphene_sqlalchemy.converter import convert_column_to_string
from graphene_sqlalchemy.converter import get_column_doc
from graphene_sqlalchemy.converter import is_column_nullable

import evalg.database.types


@convert_sqlalchemy_type.register(evalg.database.types.JsonType)
@convert_sqlalchemy_type.register(evalg.database.types.MutableJson)
@convert_sqlalchemy_type.register(evalg.database.types.NestedMutableJson)
def convert_json_to_generic_scalar(type, column, registry=None):
    return GenericScalar(
        description=get_column_doc(column),
        required=not(is_column_nullable(column)))


@convert_sqlalchemy_type.register(evalg.database.types.UtcDateTime)
@convert_sqlalchemy_type.register(evalg.database.types.UrlType)
@convert_sqlalchemy_type.register(evalg.database.types.UuidType)
def convert_custom_to_string(*args, **kwargs):
    return convert_column_to_string(*args, **kwargs)
