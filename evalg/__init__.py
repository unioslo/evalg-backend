"""
Module for bootstrapping the eValg application.
"""
import os

import flask_sqlalchemy
from flask import Flask, json, has_request_context
from flask_cors import CORS
from flask_migrate import Migrate


from . import cli
from . import default_config
from . import default_election_template_config
from . import request_id
from . import version

from .config import init_config
from .logging import init_logging
from .database.audit import audit_plugin_source, meta_plugin_source

__version__ = version.get_distribution().version


class SQLAlchemy(flask_sqlalchemy.SQLAlchemy):
    """
    Patch flask_sqlalchemy with custom params for ``create_engine()``.
    """

    def apply_driver_hacks(self, app, info, options):
        if info.drivername == "postgres":
            # We need our custom json module to be used for postgres, because
            # the engine does the json serialization.
            # Note that any change here must be co-ordinated with
            # 'evalg.database.types'
            options.update(json_serializer=json.dumps)
        super(SQLAlchemy, self).apply_driver_hacks(app, info, options)


APP_CONFIG_ENVIRON_NAME = "EVALG_CONFIG"
APP_TEMPLATE_CONFIG_ENVIRON_NAME = "EVALG_TEMPLATE_CONFIG"
"""
Name of an environment variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *gunicorn*.
"""

APP_CONFIG_FILE_NAME = "evalg_config.py"
"""Config filename in the Flask application instance path."""

APP_TEMPLATE_CONFIG_FILE_NAME = "evalg_template_config.py"
"""Election definitions."""

APP_INSTANCE_PATH_ENVIRON_NAME = "EVALG_INSTANCE_PATH"
"""Name of environment variable used to set the instance_path."""

db = SQLAlchemy()
"""Database."""

migrate = Migrate()
"""Migrations."""

cors = CORS()
"""CORS."""


def create_app(config=None, config_file=None, flask_class=Flask):
    """
    Create application.

    :rtype: Flask
    :return: The assembled and configured Flask application.
    """

    # Load a custom instance_path if set
    instance_path = os.environ.get(APP_INSTANCE_PATH_ENVIRON_NAME, default=None)

    # Setup Flask app
    app = flask_class(
        __name__,
        static_folder=None,
        instance_path=instance_path,
        instance_relative_config=True,
    )

    # Setup CLI
    cli.init_app(app)

    init_config(
        app,
        config=config,
        config_file=config_file,
        environ_name=APP_CONFIG_ENVIRON_NAME,
        default_file_name=APP_CONFIG_FILE_NAME,
        default_config=default_config,
    )

    # Load evalg_templates as config.
    # TODO: Do this another way?
    init_config(
        app,
        environ_name=APP_TEMPLATE_CONFIG_ENVIRON_NAME,
        default_file_name=APP_TEMPLATE_CONFIG_FILE_NAME,
        default_config=default_election_template_config,
    )

    # Setup logging
    init_logging(app)
    request_id.RequestId(app)

    # Setup db
    db.init_app(app)
    migrate.init_app(app, db, directory="evalg/migrations")

    # Feide Gatekeeper: Add localhost and trusted proxy subnets to whitelist
    from flask_feide_gk import proxyfix

    proxies = app.config.get("TRUSTED_PROXIES", ("127.0.0.0/8", "::1"))
    proxyfix.ProxyFix(proxies, app=app)

    # Feide Gatekeeper: Require basic auth
    from evalg import authentication

    authentication.init_app(app)

    # Authorization
    from evalg import authorization

    authorization.init_app(app=app)

    # Setup API
    from evalg import graphql

    graphql.init_app(app)

    # Setup CORS
    cors.init_app(app)

    # Setup other APIs
    from evalg import api

    api.init_app(app)

    # Add cache headers to all responses
    @app.after_request
    def set_cache_headers(response):
        response.headers["Pragma"] = "no-cache"
        response.headers["Cache-Control"] = "no-cache"
        return response

    if app.config["AUTH_ENABLED"] and app.debug:

        @app.before_request
        def log_remote_addr():
            from flask import current_app
            from flask_feide_gk import utils
            import flask

            current_app.logger.info("client-ip: %r", flask.request.remote_addr)
            current_app.logger.info(
                "x-forwarded-for: %r", utils.get_multi_header("x-forwarded-for")
            )

    @audit_plugin_source.register("remote_addr")
    def get_remote_addr():
        from flask import request, has_request_context

        if has_request_context():
            return request.remote_addr
        return None

    @audit_plugin_source.register("user_id")
    def get_user_id():
        from evalg import authentication

        if authentication.user.is_authentication_finished():
            return authentication.user.person.id
        return None

    # @meta_plugin_source.register('feide_id')
    # def get_feide_id():
    #     from evalg import authentication
    #     if authentication.user.is_authenticated():
    #         return authentication.user.dp_ids['feide']
    #     return None

    @meta_plugin_source.register("job_name")
    def get_job_name():
        import os

        if "EVALG_JOB_NAME" in os.environ:
            return os.environ["EVALG_JOB_NAME"]

    return app
