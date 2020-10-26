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


@click.command('convert-to-lamu-election',
               short_help='Converts regular election to LAMU election')
@flask.cli.with_appcontext
def convert_to_lamu_election():
    """Prompts for election-group-ID and new name for the new LAMU group"""
    from evalg.models.election import ElectionGroup
    election_group_id = input('Enter election-group UUID: ')
    try:
        election_group = evalg.db.session.query(ElectionGroup).get(
            election_group_id)
        print(f'Election-group: {election_group.name}')
        new_name_nb, new_name_nn, new_name_en = input(
            'Enter new name (nb,nn,en) separated by ",": ').split(',')
        election_group.name = {'nb': new_name_nb.strip(),
                               'nn': new_name_nn.strip(),
                               'en': new_name_en.strip()}
        print(type(election_group.elections))
        active_elections = [e for e in election_group.elections if e.active]
        if len(active_elections) != 1:
            print('Not only one active election, aborting')
            db.session.rollback()
            return
        election = active_elections[0]
        election.name = {'nb': 'Ansatte',
                         'nn': 'Tilsette',
                         'en': 'Staff'}
        poolbooks = election.pollbooks
        if len(pollbooks) != 1:
            print('Not only one pollbook, aborting')
            db.session.rollback()
        pollbooks[0].name = {'nb': 'Ansatte',
                             'nn': 'Tilsette',
                             'en': 'Staff'}
        evalg.db.session.commit()
        print(f'Done: {election_group.name}')
    except NoResultFound:
        print(f'No election group with UUID: {election_group_id} found')
        return
    except Exception as exc:
        print(f'Unable to rename election-group: {exc}')
        return


@click.command('delete-election-group',
               short_help=('Deletes the election group with its elections, '
                           'pollbooks and all other relations'))
@flask.cli.with_appcontext
def delete_election_group():
    """Prompts for election-group-ID and then for confirmation"""
    from evalg.models.election import ElectionGroup
    election_group_id = input('Enter election-group UUID: ')
    try:
        election_group = evalg.db.session.query(ElectionGroup).get(
            election_group_id)
        if election_group is None:
            print(f'Could not find election-group with UUID: '
                  f'{election_group_id}')
            return
        print(f'Election-group: {election_group.name} - '
              f'Status: {election_group.status}')
        confirmation = input('Really delete? (Type all uppercase "yes" to '
                             'confirm and ENTER to abort!): ').strip()
        if confirmation != 'YES':
            return
        # perhaps election_group.delete() can be enough
        evalg.db.session.delete(election_group)
        evalg.db.session.commit()
    except NoResultFound:
        print(f'No election group with UUID: {election_group_id} found')
        return
    except Exception as exc:
        print(f'Unable to delete election-group: {exc}')
        return


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


@click.command('rename-election-group',
               short_help='Renames the elections in a given election group')
@flask.cli.with_appcontext
def rename_election_group():
    """Prompts for election-group-ID and new name for that group"""
    from evalg.models.election import ElectionGroup
    election_group_id = input('Enter election-group UUID: ')
    try:
        election_group = evalg.db.session.query(ElectionGroup).get(
            election_group_id)
        if election_group is None:
            print(f'Could not find election-group with UUID: '
                  f'{election_group_id}')
            return
        print(f'Election-group: {election_group.name}')
        new_name_nb, new_name_nn, new_name_en = input(
            'Enter new name (nb,nn,en) separated by ",": ').split(',')
        election_group.name = {'nb': new_name_nb.strip(),
                               'nn': new_name_nn.strip(),
                               'en': new_name_en.strip()}
        evalg.db.session.commit()
        print(f'Done: {election_group.name}')
    except NoResultFound:
        print(f'No election group with UUID: {election_group_id} found')
        return
    except Exception as exc:
        print(f'Unable to rename election-group: {exc}')
        return


@click.command('soft-delete-election-group',
               short_help=('Sets deleted = True for a given election-group'))
@flask.cli.with_appcontext
def soft_delete_election_group():
    """Prompts for election-group-ID and then for confirmation"""
    from evalg.models.election import ElectionGroup
    election_group_id = input('Enter election-group UUID: ')
    try:
        election_group = evalg.db.session.query(ElectionGroup).get(
            election_group_id)
        if election_group is None:
            print(f'Could not find election-group with UUID: '
                  f'{election_group_id}')
            return
        print(f'Election-group: {election_group.name} - '
              f'Status: {election_group.status}')
        confirmation = input(
            'Really mark as deleted? (Type all uppercase "yes" '
            'to confirm and ENTER to abort!): ').strip()
        if confirmation != 'YES':
            return
        election_group.delete()
        evalg.db.session.commit()
    except NoResultFound:
        print(f'No election group with UUID: {election_group_id} found')
        return
    except Exception as exc:
        print(f'Unable to mark election-group as deleted: {exc}')
        return


commands = (add_election_group_admin,
            convert_to_lamu_election,
            delete_election_group,
            list_administrated_groups,
            rename_election_group,
            soft_delete_election_group)


def init_app(app):
    """Add commands to flask application cli."""
    for command in commands:
        app.cli.add_command(command)
