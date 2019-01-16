"""
Command line interface for the evalg application.
"""
from . import flask_cmds
from . import db_cmds


def init_app(app):
    """ Add all evalg commands to flask application cli. """
    flask_cmds.init_app(app)
    db_cmds.init_app(app)
