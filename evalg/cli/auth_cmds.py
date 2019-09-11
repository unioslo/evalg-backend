"""
Commands for importing units.
"""
import click
import flask
import flask.cli

from flask import current_app

import evalg


# TODO: Use the corresponding get_or_create methods in proc.authz
#   Importing these methods brakes pytest, as we a missing context in proc.
#   This can be fixed by not inherit from `db.Model` i models.base.

def get_or_create_group(group_name):
    """Ensure existence of a group."""
    group = evalg.models.group.Group.query.filter_by(
        name=group_name).first()
    if group:
        current_app.logger.info('Found entitlement group, name: %s',
                                group_name)
        return group
    current_app.logger.info('Creating entitlement group, name: %s',
                            group_name)
    group = evalg.models.group.Group()
    group.name = group_name
    evalg.db.session.add(group)
    evalg.db.session.flush()


def get_or_create_group_principal(group):
    """Ensure existence of a group principal."""
    principal = evalg.models.authorization.GroupPrincipal.query.filter_by(
        group_id=group.id
    ).first()
    if principal:
        current_app.logger.info('Found principal for group=%s',
                                group.id)
        return principal

    current_app.logger.info('Creating principal for group=%s',
                            group.id)
    principal = evalg.models.authorization.GroupPrincipal()
    principal.group_id = group.id
    evalg.db.session.add(principal)
    evalg.db.session.flush()
    return principal


def get_or_create_election_group_role(role_name, principal):
    """Ensure existence of a election group role."""
    role = evalg.models.authorization.ElectionGroupRole.query.filter_by(
        name=role_name,
        principal=principal,
        global_role=True,
    ).first()
    if role:
        current_app.logger.info('Found role for grant_id=%s', role.grant_id)
        return role

    current_app.logger.info('Creating role for %s', role_name)
    role = evalg.models.authorization.ElectionGroupRole()
    role.principal = principal
    role.name = role_name
    role.global_role = True

    evalg.db.session.add(role)
    evalg.db.session.flush()
    current_app.logger.info(role)


@click.command('init-authorization',
               short_help='Create entitlement groups if missing.')
@flask.cli.with_appcontext
def create_groups():
    import os
    os.environ['EVALG_JOB_NAME'] = "init-authorization"
    config = flask.current_app.config
    mapping = config.get('FEIDE_ENTITLEMENT_MAPPING')
    current_app.logger.info('Initiating global authorization groups and '
                            'principals')
    for role_name in mapping:
        current_app.logger.info('Creating role=%s', role_name)
        group = get_or_create_group(role_name)
        group_principal = get_or_create_group_principal(
            group
        )
        role = get_or_create_election_group_role(role_name, group_principal)

    evalg.db.session.commit()


commands = tuple((
    create_groups,
))


def init_app(app):
    """ Add commands to flask application cli. """
    for command in commands:
        app.cli.add_command(command)
