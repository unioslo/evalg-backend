"""
The evalg graphql APIs.
"""
import graphene
from flask_graphql import GraphQLView
from graphene.types.generic import GenericScalar
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphene_sqlalchemy.converter import convert_column_to_string
from graphene_sqlalchemy.converter import get_column_doc
from graphene_sqlalchemy.converter import is_column_nullable

import evalg.database.types
from . import entities
from . import mutations
from . import queries


# Configure custom conversions

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


schema = graphene.Schema(
    query=queries.ElectionQuery,
    mutation=mutations.Mutations,
    types=[entities.ElectionGroup])


def init_app(app):
    from evalg.graphql.middleware import timing_middleware, auth_middleware

    middleware = [timing_middleware]
    if app.config.get('AUTH_ENABLED'):
        middleware.append(auth_middleware)

    app.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            batch=True,
            graphiql=True,
            middleware=middleware
        ))
