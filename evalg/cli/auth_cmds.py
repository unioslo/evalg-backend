"""
Commands for importing units.
"""
import click
import flask
import flask.cli

from flask import current_app

import evalg


def add_group(group_name):
    current_app.logger.info('Adding missing entitlement group, name: %s',
                            group_name)
    group = evalg.models.group.Group()
    group.name = group_name
    evalg.db.session.add(group)
    evalg.db.session.flush()


def get_group(group_name):
    return evalg.models.group.Group.query.filter_by(
        name=group_name).first()


@click.command('create-groups',
               short_help='Create entitlement groups if missing.')
@flask.cli.with_appcontext
def create_groups():
    import os
    os.environ['EVALG_JOB_NAME'] = "create-units"
    config = flask.current_app.config
    mapping = config.get('FEIDE_ENTITLEMENT_MAPPING')
    changes = False
    for group_name in mapping:
        current_app.logger.info('Checking if group %s exists', group_name)
        if not get_group(group_name):
            add_group(group_name)
            changes = True
    if changes:
        evalg.db.session.commit()


commands = tuple((
    create_groups,
))


def init_app(app):
    """ Add commands to flask application cli. """
    for command in commands:
        app.cli.add_command(command)
