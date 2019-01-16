"""
Module for bootstrapping the eValg application.
"""
import os

from flask import Flask, json
from flask_apispec.extension import FlaskApiSpec
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix

from . import cli
from . import default_config
from . import default_election_template_config
from . import request_id
from . import version
from .config import init_config
from .logging import init_logging


__version__ = version.get_distribution().version


class HackSQLAlchemy(SQLAlchemy):
    """
    Ugly way to get SQLAlchemy engine to pass the Flask JSON serializer
    to `create_engine`.

    See https://github.com/mitsuhiko/flask-sqlalchemy/pull/67/files
    """

    def apply_driver_hacks(self, app, info, options):
        options.update(json_serializer=json.dumps)
        super(HackSQLAlchemy, self).apply_driver_hacks(app, info, options)


APP_CONFIG_ENVIRON_NAME = 'EVALG_CONFIG'
"""
Name of an environmet variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *gunicorn*.
"""

APP_CONFIG_FILE_NAME = 'evalg_config.py'
"""Config filename in the Flask application instance path."""

APP_TEMPLATE_CONFIG_FILE_NAME = 'evalg_template_config.py'
"""Election definitions."""

APP_INSTANCE_PATH_ENVIRON_NAME = 'EVALG_INSTANCE_PATH'
"""Name of environment variable used to set the instance_path."""

db = SQLAlchemy()
"""Database."""

ma = Marshmallow()
"""Marshmallow."""

migrate = Migrate()
"""Migrations."""

docs = FlaskApiSpec()
"""API documentation."""

cors = CORS()
"""CORS."""


def create_app(config=None, flask_class=Flask):
    """
    Create application.

    :rtype: Flask
    :return: The assembled and configured Flask application.
    """

    # Load a custom instance_path if set
    instance_path = os.environ.get(
        APP_INSTANCE_PATH_ENVIRON_NAME,
        default=None)

    # Setup Flask app
    app = flask_class(__name__,
                      static_folder=None,
                      instance_path=instance_path,
                      instance_relative_config=True)

    # Setup CLI
    cli.init_app(app)

    init_config(app, config,
                environ_name=APP_CONFIG_ENVIRON_NAME,
                default_file_name=APP_CONFIG_FILE_NAME,
                default_config=default_config)

    # Load evalg_templates as config.
    # TODO: Do this another way?
    init_config(app, config,
                environ_name=APP_CONFIG_ENVIRON_NAME,
                default_file_name=APP_TEMPLATE_CONFIG_FILE_NAME,
                default_config=default_election_template_config)

    if app.config.get('NUMBER_OF_PROXIES', None):
        app.wsgi_app = ProxyFix(app.wsgi_app,
                                num_proxies=app.config.get(
                                    'NUMBER_OF_PROXIES'))

    # Setup logging
    init_logging(app)
    request_id.init_app(app)

    # Setup db
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db, directory='evalg/migrations')

    # Setup API
    docs.init_app(app)

    from evalg import api
    api.init_app(app)

    from evalg import graphql
    graphql.init_app(app)

    # Setup CORS
    cors.init_app(app)

    # Add cache headers to all responses
    @app.after_request
    def set_cache_headers(response):
        response.headers['Pragma'] = 'no-cache'
        response.headers['Cache-Control'] = 'no-cache'
        return response

    return app
