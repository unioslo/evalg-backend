"""
Command line interface for the evalg application.
"""
from . import auth_cmds
from . import db_cmds
from . import flask_cmds
from . import unit_cmds


def init_app(app):
    """ Add all evalg commands to flask application cli. """
    db_cmds.init_app(app)
    flask_cmds.init_app(app)
    unit_cmds.init_app(app)
    auth_cmds.init_app(app)
