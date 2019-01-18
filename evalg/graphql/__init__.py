"""
The evalg graphql APIs.
"""
import graphene
from flask_graphql import GraphQLView

from . import entities
from . import mutations
from . import queries

    census_file_types = graphene.List(graphene.String)

    def resolve_census_file_types(self, info, **kwargs):
       return CensusFileParser.get_supported_file_types()


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
