import pytest

import evalg.database.query
from evalg import create_app, db
from evalg.models.election import ElectionGroup, Election
from evalg.models.pollbook import PollBook

pytest_plugins = ['pytest-flask-sqlalchemy']


@pytest.fixture(scope='session')
def config():
    """ Application config. """
    class Config(object):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite://'
        AUTH_ENABLED = True
        AUTH_METHOD = 'feide_mock'
        FEIDE_BASIC_REQUIRE = False

    return Config()


@pytest.yield_fixture(scope='session')
def database(app, request):
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()


@pytest.fixture(scope='session')
def app(config):
    app = create_app(config=config)
    return app


@pytest.fixture(scope='session')
def _db(app, database):
    """
    Provide the transactional fixtures with access to the database via a
    Flask-SQLAlchemy database connection.

    This fixture is expected by `pytest-flask-sqlalchemy
    """
    return database


@pytest.fixture
def group_foo(db_session):
    data = {
        'name': {
            'nb': 'Foo',
            'en': 'Foo',
        },
        'type': 'single_election',
        'description': {
            'nb': 'Description foo',
            'en': 'Description foo',
        }
    }
    group = evalg.database.query.get_or_create(
        db_session, ElectionGroup, **data)
    db_session.add(group)
    db_session.flush()
    return group


@pytest.fixture
def election_bar(db_session, group_foo):
    data = {
        'name': {
            'nb': 'Bar',
            'en': 'Bar',
        },
        'type': 'single_election',
        'description': {
            'nb': 'Description foo',
            'en': 'Description foo',
        },
        'group_id': group_foo.id,
    }
    election = evalg.database.query.get_or_create(
        db_session, Election, **data)
    db_session.add(election)
    db_session.flush()
    return election


@pytest.fixture
def pollbook_one(db_session, election_bar):
    data = {
        'name': {
            'nb': 'Pollbook One',
            'en': 'Pollbook One',
        },
        'election_id': election_bar.id,
    }
    pollbook = evalg.database.query.get_or_create(
        db_session, PollBook, **data)
    db_session.add(pollbook)
    db_session.flush()
    return pollbook
