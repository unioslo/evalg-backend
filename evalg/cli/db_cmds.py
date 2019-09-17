"""
Commands for interacting with the evalg database.

This module extend the existing flask cli with custom commands for interacting
with the evalg database.
"""
import click
import flask.cli
from flask import current_app, g


def start_request(*args, **kwargs):
    """
    Make a request context.

    http://flask.pocoo.org/docs/1.0/api/#flask.Flask.test_request_context
    """
    ctx = current_app.test_request_context(*args, **kwargs)
    ctx.push()
    current_app.preprocess_request()
    return ctx


def end_request(ctx, response=None):
    """
    End a request context with a response.
    """
    current_app.process_response(response or current_app.response_class())
    ctx.pop()


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
    db.drop_all()
    db.create_all()


def shell_context():
    """ Shell context. """
    import uuid
    from evalg import db, models
    from evalg.authentication import user
    from evalg.database.formatting import pretty_format
    from pprint import pprint
    context = {
        'save': save_object,
        'show_query': show_query,
        'start_request': start_request,
        'end_request': end_request,
        'db': db,
        'Candidate': models.candidate.Candidate,
        'Election': models.election.Election,
        'ElectionGroup': models.election.ElectionGroup,
        'ElectionList': models.election_list.ElectionList,
        'ElectionGroupRole': models.authorization.ElectionGroupRole,
        'Envelope': models.ballot.Envelope,
        'Group': models.group.Group,
        'Person': models.person.Person,
        'PersonExternalId': models.person.PersonExternalId,
        'pretty': lambda *a, **kw: print(pretty_format(*a, **kw)),
        'PollBook': models.pollbook.PollBook,
        'Principal': models.authorization.Principal,
        'PersonPrincipal': models.authorization.PersonPrincipal,
        'GroupPrincipal': models.authorization.GroupPrincipal,
        'Role': models.authorization.Role,
        'OU': models.ou.OrganizationalUnit,
        'models': models,
        'query': db.session.query,
        'user': user,
        'uuid4': uuid.uuid4,
        'Voter': models.voter.Voter,
        'Vote': models.votes.Vote,
        'VoteRecord': models.votes.VoteRecord,
        'g': g,
        'wipe_db': wipe_db,
    }
    print('\nShell context:')
    pprint(context)
    print()
    return context


commands = tuple((
))


def init_app(app):
    """ Add commands to flask application cli. """
    app.shell_context_processor(shell_context)
    for command in commands:
        app.cli.add_command(command)
