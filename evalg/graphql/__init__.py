"""
The evalg graphql APIs.
"""
import logging

import graphene
from flask_graphql import GraphQLView

from . import entities
from . import mutations
from . import queries

logger = logging.getLogger(__name__)
schema = graphene.Schema(
    query=queries.ElectionQuery,
    mutation=mutations.Mutations,
    types=[entities.ElectionGroup])


def init_app(app):
    from evalg.graphql import middleware

    mw = [
        middleware.logging_middleware,
        middleware.timing_middleware,
    ]
    if app.config.get('AUTH_ENABLED'):
        mw.append(middleware.auth_middleware)

    app.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            batch=True,
            graphiql=True,
            middleware=mw
        ))
