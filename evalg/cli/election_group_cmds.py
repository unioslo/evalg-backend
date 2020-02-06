"""Commands for manually listing and adding administrators"""
import logging

import click

import flask
import flask.cli

from sqlalchemy.orm.exc import NoResultFound

import evalg


logger = logging.getLogger(__name__)


@click.command('add-election-group-admin',
               short_help=('Adds election-group admin (Feide-ID) for '
                           'a given election group (UUID).'))
@flask.cli.with_appcontext
def add_election_group_admin():
    """Prompts and adds admin for a given election_group"""
    from evalg.proc.authz import add_election_group_role
    from evalg.models.authorization import PersonIdentifierPrincipal
    from evalg.models.election import ElectionGroup
    admin_feide_id = input('Enter admin Feide-ID: ').strip()
    election_group_id = input('Enter election-group UUID: ')
    election_group = evalg.db.session.query(ElectionGroup).get(
        election_group_id)
    if election_group is None:
        print(f'Could not find election-group with UUID: {election_group_id}')
        return
    try:
        pi_principal = evalg.db.session.query(
            PersonIdentifierPrincipal).filter_by(id_type='feide_id',
                                                 id_value=admin_feide_id).one()
    except NoResultFound:
        if (
                input(f'No PersonIdentifierPrincipal with feide_id '
                      f'{admin_feide_id} found. '
                      'Press all upper case "yes" to add: ').strip() != 'YES'
        ):
            return
        pi_principal = PersonIdentifierPrincipal(id_type='feide_id',
                                                 id_value=admin_feide_id)
        evalg.db.session.add(pi_principal)
        evalg.db.session.flush()

    add_election_group_role(evalg.db.session,
                            election_group=election_group,
                            principal=pi_principal,
                            role_name='admin')
    evalg.db.session.commit()
    print(f'{admin_feide_id} -> {election_group_id}', flush=True)


@click.command('list-administrated-groups',
               short_help='Lists all election-groups where Feide-ID is admin')
@flask.cli.with_appcontext
def list_administrated_groups():
    """Prompts for Feide-ID and lists election-groups Feide-ID is admin"""
    from evalg.models.authorization import (ElectionGroupRole,
                                            PersonIdentifierPrincipal,
                                            Role)
    from evalg.models.election import ElectionGroup
    admin_feide_id = input('Enter admin Feide-ID: ').strip()
    try:
        pi_principal = evalg.db.session.query(
            PersonIdentifierPrincipal).filter_by(
                id_type='feide_id', id_value=admin_feide_id).one()
    except NoResultFound:
        print(f'No admin with Feide-ID: {admin_feide_id} found')
        return
    results = evalg.db.session.query(
        ElectionGroup,
        ElectionGroupRole,
        Role).filter(
            ElectionGroup.id == ElectionGroupRole.group_id,
            Role.grant_id == ElectionGroupRole.grant_id,
            Role.principal_id == pi_principal.id).all()
    if not results:
        print(f'No election groups with admin {admin_feide_id} found')
        return
    for election_group, _, _ in results:
        print(f"{election_group.id}: {election_group.name['nb']}")


commands = (add_election_group_admin, list_administrated_groups)


def init_app(app):
    """ Add commands to flask application cli. """
    for command in commands:
        app.cli.add_command(command)
