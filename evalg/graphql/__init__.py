"""
The evalg graphql APIs.
"""
import logging

import flask
import flask_graphql
import graphene

from evalg import db
from evalg.authentication import user

# We need to import our converters before any entities are defined.
from . import converter  # noqa: F401
from . import mutations
from . import nodes
from . import queries

logger = logging.getLogger(__name__)

schema = graphene.Schema(
    query=queries.ElectionQuery,
    mutation=mutations.ElectionMutations,
    types=[nodes.election_group.ElectionGroup])


class ProperView(flask_graphql.GraphQLView):

    context = None

    def __init__(self, context=context, **kwargs):
        super(ProperView, self).__init__(**kwargs)
        self.context = context

    def get_context(self):
        return self.context


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
        view_func=ProperView.as_view(
            'graphql',
            schema=schema,
            batch=True,
            context={
                'session': db.session,
                'request': flask.request,
                'user': user,
            },
            graphiql=True,
            middleware=mw
        ))
