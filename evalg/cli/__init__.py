"""
Command line interface for the evalg application.
"""
from . import auth_cmds
from . import db_cmds
from . import election_group_cmds
from . import email_cmds
from . import flask_cmds
from . import key_cmds
from . import unit_cmds


def init_app(app):
    """ Add all evalg commands to flask application cli. """
    auth_cmds.init_app(app)
    db_cmds.init_app(app)
    election_group_cmds.init_app(app)
    email_cmds.init_app(app)
    flask_cmds.init_app(app)
    key_cmds.init_app(app)
    unit_cmds.init_app(app)
