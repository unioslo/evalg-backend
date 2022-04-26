"""
The evalg graphql APIs.
"""
import logging

import flask
import flask_graphql
import graphene
from graphene_file_upload.flask import FileUploadGraphQLView

from evalg.authentication import basic

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
    types=[nodes.election_group.ElectionGroup],
)


class ContextGraphQLView(flask_graphql.GraphQLView):

    context = None

    def __init__(self, context=context, **kwargs):
        super(ContextGraphQLView, self).__init__(**kwargs)
        self.context = context

    def get_context(self):
        return self.context


class EvalgGraphQLView(ContextGraphQLView, FileUploadGraphQLView):
    pass


def get_context():
    return {
        "session": db.session,
        "request": flask.request,
        "user": user,
    }


def get_test_context(db_session):
    """
    Context for testing.

    We use the pytest-flask-sqlalchemy plugin to do transaction rollbacks
    after tests. This context enables us to pass the pytest-flask-sqlalchemy
    db_session to the test graphql client.
    """
    return {
        "session": db_session,
        "request": flask.request,
        "user": user,
    }


def init_app(app):
    from evalg.graphql import middleware

    mw = [
        middleware.logging_middleware,
        middleware.timing_middleware,
    ]
    if app.config.get("AUTH_ENABLED"):
        mw.append(middleware.auth_middleware)

    graphql_view = EvalgGraphQLView.as_view(
        "graphql",
        schema=schema,
        batch=True,
        context=get_context(),
        graphiql=True,
        middleware=mw,
    )

    app.add_url_rule("/graphql", view_func=basic.require(graphql_view))
