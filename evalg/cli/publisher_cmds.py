"""
Commands for adding and removing publishers.
"""
import click
import flask.cli

from sqlalchemy.orm.exc import NoResultFound

import evalg


@click.command('remove-publisher',
               short_help='Remove the publisher role from a user')
@click.argument('feide_id')
@flask.cli.with_appcontext
def remove_publisher(feide_id):
    import os
    os.environ['EVALG_JOB_NAME'] = "remove-publisher"
    try:
        person_extenal_id = evalg.db.session.query(
            evalg.models.person.PersonExternalId).filter_by(
            id_type='feide_id',
            id_value=feide_id).all()
    except NoResultFound:
        print(f'No person with feide-id {feide_id} found!')
        return

    if len(person_extenal_id) == 0:
        print(f'No person with feide-id {feide_id} found!')
        return
    elif len(person_extenal_id) > 1:
        print(f'Found multiple people with the same id. '
              'Something is wrong. Exiting..')
        return
    person = person_extenal_id[0].person
    group = evalg.proc.group.get_group_by_name(evalg.db.session, 'publisher')

    if not evalg.proc.group.is_member_of_group(
            evalg.db.session,
            group,
            person):
        print(f'{feide_id} does not have the publisher role.')
        return

    evalg.proc.group.remove_person_from_group(evalg.db.session, group, person)
    print(f'Removed {feide_id} as a publisher.')
    evalg.db.session.commit()


@click.command('add-publisher',
               short_help='Add publisher role to user')
@click.argument('feide_id')
@flask.cli.with_appcontext
def add_publisher(feide_id):
    import os
    os.environ['EVALG_JOB_NAME'] = "add-publisher"
    try:
        person_extenal_id = evalg.db.session.query(
            evalg.models.person.PersonExternalId).filter_by(
            id_type='feide_id',
            id_value=feide_id).all()
    except NoResultFound:
        print(f'No person with feide-id {feide_id} found!')
        return

    if len(person_extenal_id) == 0:
        print(f'No person with feide-id {feide_id} found!')
        return
    elif len(person_extenal_id) > 1:
        print(f'Found multiple people with the same id. '
              'Something is wrong. Exiting..')
        return
    person = person_extenal_id[0].person
    group = evalg.proc.group.get_group_by_name(evalg.db.session, 'publisher')

    if evalg.proc.group.is_member_of_group(evalg.db.session, group, person):
        print(f'{feide_id} is already a publisher.')
        return

    membership = evalg.proc.group.add_person_to_group(
        evalg.db.session,
        group,
        person)
    print(f'Added {feide_id} as publisher. {membership}')
    evalg.db.session.commit()


commands = tuple((
    add_publisher,
    remove_publisher,
))


def init_app(app):
    """ Add commands to flask application cli. """
    for command in commands:
        app.cli.add_command(command)
