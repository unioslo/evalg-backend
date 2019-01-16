"""
Module for bootstrapping the ballotbox application.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.contrib.fixers import ProxyFix

from evalg import request_id
from evalg import version
from evalg.config import init_config
from evalg.logging import init_logging

from ballotbox import default_config
from ballotbox import api


__version__ = version.get_distribution().version


APP_CONFIG_ENVIRON_NAME = 'BALLOTBOX_CONFIG'
"""
Name of an environmet variable to read config file name from.

This is a useful method to set a config file if the application is started
through a third party application server like *gunicorn*.
"""

APP_CONFIG_FILE_NAME = 'ballotbox_config.py'
"""Config filename in the Flask application instance path."""


class WsgiApp(object):
    """Wsgi app proxy object."""

    @staticmethod
    def create(config=None, flask_class=Flask):
        """
        Create application.

        :rtype: Flask
        :return: The assembled and configured Flask application.
        """
        # Setup Flask app
        app = flask_class(__name__,
                          static_folder=None,
                          instance_relative_config=True)

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

        # Setup API
        api.init_app(app)

        # Add cache headers to all responses
        @app.after_request
        def set_cache_headers(response):
            response.headers['Pragma'] = 'no-cache'
            response.headers['Cache-Control'] = 'no-cache'
            return response

        return app

    @property
    def app(self):
        """Lazily create the application."""
        if not hasattr(self, '_app'):
            self._app = self.create()
        return self._app

    def __call__(self, *args, **kwargs):
        """Run the application on a request."""
        return self.app(*args, **kwargs)


wsgi = WsgiApp()
"""WSGI app."""

app = wsgi.app
"""Flask app."""

db = SQLAlchemy(app)
"""Database."""

migrate = Migrate(app, db)
"""Migrations."""
