"""
Commands for importing units.
"""
import evalg
from evalg.unit_importer.importer import UnitImporter

import click
import flask
import flask.cli
import logging

logger = logging.getLogger(__name__)


def add_unit(unit):
    logger.info('Adding new unit, ou: %s, name: %s',
                unit['external_id'], unit['name'])
    u = evalg.models.ou.OrganizationalUnit()
    u.name = unit['name']
    u.external_id = unit['external_id']
    u.tag = unit['tag']
    evalg.db.session.add(u)
    evalg.db.session.flush()


def update_unit(unit, new_unit):
    """Updates changes to a units name or tag"""
    logger.info('Checking for changes to existing unit, ou: %s, name: %s',
                unit.external_id,
                unit.name)

    if unit.name != new_unit['name']:
        logger.info('Found updated name, ou: %s, old_name: %s, new_name: %s',
                    unit.external_id,
                    unit.name,
                    new_unit['name'])
        unit.name = new_unit['name']

    if unit.tag != new_unit['tag']:
        logger.info('Found updated tag, ou: %s, old_tag: %s, new_tag: %s',
                    unit.external_id,
                    unit.tag,
                    new_unit['tag'])
        unit.tag = new_unit['tag']

    evalg.db.session.flush()


def get_unit(external_id):
    return evalg.models.ou.OrganizationalUnit.query.filter_by(
        external_id=external_id).first()


@click.command('import-units',
               short_help='Import units.')
@flask.cli.with_appcontext
def import_units():
    import os
    os.environ['EVALG_JOB_NAME'] = "import-units"
    config = flask.current_app.config
    importer_type = config.get('UNIT_IMPORTER')

    unit_importer = evalg.unit_importer.importer.UnitImporter.factory(
        importer_type['type'],
        importer_type['config'],
    )

    for unit in unit_importer.get_units():
        old_unit = get_unit(unit['external_id'])

        if old_unit:
            update_unit(old_unit, unit)
        else:
            add_unit(unit)

    evalg.db.session.commit()


commands = tuple((
    import_units,
))


def init_app(app):
    """ Add commands to flask application cli. """
    for command in commands:
        app.cli.add_command(command)
