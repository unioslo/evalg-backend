#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module for bootstrapping the eValg application.

"""
from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_apispec.extension import FlaskApiSpec
from flask_cors import CORS
from werkzeug.contrib.fixers import ProxyFix
import pkg_resources

from evalg.utils import convert_json
from evalg_common.configuration import init_config
from evalg_common.logging import init_logging
from evalg_common import request_id
from evalg_common import cli as common_cli

from evalg import default_config
from evalg import cli

DISTRIBUTION_NAME = 'evalg'

def get_distribution():
    """ Get the distribution object for this single module dist. """
    try:
        return pkg_resources.get_distribution(DISTRIBUTION_NAME)
    except pkg_resources.DistributionNotFound:
        return pkg_resources.Distribution(
            project_name=DISTRIBUTION_NAME,
            version='0.0.0',
            location=os.path.dirname(__file__))

__version__ = get_distribution().version


class HackSQLAlchemy(SQLAlchemy):
    """ Ugly way to get SQLAlchemy engine to pass the Flask JSON serializer
    to `create_engine`.

    See https://github.com/mitsuhiko/flask-sqlalchemy/pull/67/files

    """
    def apply_driver_hacks(self, app, info, options):
        options.update(json_serializer=json.dumps)
        super(HackSQLAlchemy, self).apply_driver_hacks(app, info, options)


APP_CONFIG_ENVIRON_NAME = 'EVALG_CONFIG'
""" Name of an environmet variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *gunicorn*.
"""

APP_CONFIG_FILE_NAME = 'evalg_config.py'
""" Config filename in the Flask application instance path. """

db = HackSQLAlchemy()
""" Database. """

ma = Marshmallow()
""" Marshmallow. """

migrate = Migrate()
""" Migrations. """

docs = FlaskApiSpec()
""" API documentation. """

cors = CORS()
""" CORS. """


def create_app(config=None, flask_class=Flask):
    """ Create application.

    :rtype: Flask
    :return: The assembled and configured Flask application.
    """
    # Setup Flask app
    app = flask_class(__name__,
                      static_folder=None,
                      instance_relative_config=True)

    # Setup CLI
    common_cli.init_app(app)
    cli.init_app(app)

    init_config(app, config,
                environ_name=APP_CONFIG_ENVIRON_NAME,
                default_file_name=APP_CONFIG_FILE_NAME,
                default_config=default_config)

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
    print(docs)
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
