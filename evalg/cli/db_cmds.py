"""
Commands for interacting with the evalg database.

This module extend the existing flask cli with custom commands for interacting
with the evalg database.
"""
import click
import flask.cli


def save_object(obj):
    from evalg import db
    db.session.add(obj)
    db.session.commit()
    print("Saved {}".format(obj))


def show_query(query):
    from sqlalchemy.dialects import postgresql
    compiled = query.statement.compile(dialect=postgresql.dialect(),
                                       compile_kwargs={'literal_binds': True})
    print(str(compiled))


def import_ous():
    """ Use flask_fixtures to populate tables. """
    import json
    from evalg.models.ou import OrganizationalUnit
    from evalg import db
    f = open('ou_dump.json')
    ou_dump = json.load(f)
    for tag in ou_dump:
        print(tag)
        for ou in ou_dump[tag]:
            print(ou)
            new_ou = OrganizationalUnit()
            new_ou.name = ou['name']
            new_ou.external_id = ou['external_id']
            new_ou.tag = tag
            db.session.add(new_ou)
    db.session.commit()


def wipe_db():
    from evalg import db
    import flask_fixtures
    from evalg.fixtures import populate_tables
    db.drop_all()
    db.create_all()
    flask_fixtures.setup(populate_tables.Populator)


def shell_context():
    """ Shell context. """
    from evalg import db, models
    from evalg.database.formatting import pretty_format
    from pprint import pprint
    context = {
        'save': save_object,
        'show_query': show_query,
        'db': db,
        'Candidate': models.candidate.Candidate,
        'Election': models.election.Election,
        'ElectionGroup': models.election.ElectionGroup,
        'ElectionList': models.election_list.ElectionList,
        'ElectionRole': models.authorization.ElectionRole,
        'ElectionGroupRole': models.authorization.ElectionGroupRole,
        'Group': models.group.Group,
        'Person': models.person.Person,
        'pretty': lambda *a, **kw: print(pretty_format(*a, **kw)),
        'PollBook': models.pollbook.PollBook,
        'Principal': models.authorization.Principal,
        'PersonPrincipal': models.authorization.PersonPrincipal,
        'GroupPrincipal': models.authorization.GroupPrincipal,
        'Role': models.authorization.Role,
        'OU': models.ou.OrganizationalUnit,
        'Voter': models.voter.Voter,
        'wipe_db': wipe_db
    }
    print('\nShell context:')
    pprint(context)
    print()
    return context


@click.command('populate-tables',
               short_help='Populate tables with example data.')
@flask.cli.with_appcontext
def populate_tables():
    """ Use flask_fixtures to populate tables. """
    import flask_fixtures
    from evalg.fixtures import populate_tables
    flask_fixtures.setup(populate_tables.Populator)


@click.command('recreate-tables',
               short_help='Recreate tables with db.drop_all() and '
               'db.create_all()')
@flask.cli.with_appcontext
def recreate_tables():
    from evalg import db
    db.drop_all()
    db.create_all()


commands = tuple((
    populate_tables,
    recreate_tables,
))


def init_app(app):
    """ Add commands to flask application cli. """
    app.shell_context_processor(shell_context)
    for command in commands:
        app.cli.add_command(command)
