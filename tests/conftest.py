import pytest

import evalg.database.query
from evalg import create_app, db
from evalg.models.candidate import Candidate
from evalg.models.election import ElectionGroup, Election
from evalg.models.election_list import ElectionList
from evalg.models.person import Person, PersonExternalId
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


@pytest.fixture
def person_foo(db_session):
    """One person fixture."""
    data = {
        'email': 'foo@bar.org',
        'display_name': 'Foo Bar',
    }

    identifiers = [
        {
            "id_type": "feide_id",
            "id_value": "foo@bar.org",
        },
        {
            "id_type": "feide_user_id",
            "id_value": "a6733d24-8987-44b6-8cd0-308030710aa2",
        },
        {
            "id_type": "uid",
            "id_value": "foo@bar.org",
        },
        {
            "id_type": "nin",
            "id_value": "12128812345",
        },
    ]

    person = evalg.database.query.get_or_create(
        db_session, Person, **data)

    for identifier in identifiers:
        id_obj = PersonExternalId(
            person=person.id,
            id_type=identifier['id_type'],
            id_value=identifier['id_value']
        )
        person.identifiers.append(id_obj)

    db_session.add(person)
    db_session.flush()
    return person


@pytest.fixture
def persons(db_session):
    """Multiple persons fixture."""
    data = [
        {
            'email': 'foo@example.org',
            'display_name': 'Foo Foo',
        },
        {
            'email': 'bar@example.org',
            'display_name': 'Bar Bar',
        },
    ]

    identifiers = [
        [
            {
                "id_type": "feide_id",
                "id_value": "foo@bar.org",
            },
            {
                "id_type": "feide_user_id",
                "id_value": "a6733d24-8987-44b6-8cd0-308030710aa2",
            },
            {
                "id_type": "uid",
                "id_value": "foo",
            },
            {
                "id_type": "nin",
                "id_value": "12128812345",
            },
        ],
        [
            {
                "id_type": "feide_id",
                "id_value": "bar@baz.org",
            },
            {
                "id_type": "feide_user_id",
                "id_value": "a6733d24-8987-55b6-8cd0-308030710aa2",
            },
            {
                "id_type": "uid",
                "id_value": "bar",
            },
            {
                "id_type": "nin",
                "id_value": "12128812346",
            },
        ]
    ]

    persons = [evalg.database.query.get_or_create(
        db_session, Person, **x) for x in data]

    for i, person in enumerate(persons):
        for identifier in identifiers[i]:
            id_obj = evalg.database.query.get_or_create(
                db_session, PersonExternalId, **identifier)
            person.identifiers.append(id_obj)
        db_session.add(person)
    db_session.flush()

    return {str(x.id): x for x in persons}


@pytest.fixture
def election_lists_foo(db_session, election_bar):
    """Election lists fixture, with candidates."""
    data = [
        {
            'name': {
                "nb": "Vitenskapelig ansatte",
                "nn": "Vitskapeleg tilsette",
                'en': 'Academic staff',
            },
            "description": {
                "nb": "Vitenskapelig ansatte",
                "nn": "Vitskapeleg tilsette",
                "en": "Academic staff"
            },
            "information_url": "https://uio.no",
            'election_id': election_bar.id,
        },
        {
            'name': {
                "nb": "Studenter",
                "nn": "Studentar",
                'en': 'Students',
            },
            "description": {
                "nb": "Studenter",
                "nn": "Studentar",
                "en": "students"
            },
            "information_url": "https://uio.no",
            'election_id': election_bar.id,
        }
    ]

    candidate_data = [
        {
            "name": "Peder Aas",
            "meta": {
                "gender": "Male"
            },
            "information_url": "http://uio.no",
            "priority": 0,
            "pre_cumulated": True,
            "user_cumulated": False
        },
        {
            "name": "Marte Kirkerud",
            "meta": {
                "gender": "female"
            },
            "information_url": "http://uio.no",
            "priority": 0,
            "pre_cumulated": False,
            "user_cumulated": False
        },
    ]

    candidate_team_data = [
        {
            "name": "Peder Aas",
            "meta": {
                "coCandidates": [
                    {"name": "Marte Kirkerud"},
                    {"name": "Lars Holm"},
                ]
            },
            "information_url": "http://uio.no",
            "priority": 0,
            "pre_cumulated": True,
            "user_cumulated": False
        },
    ]

    election_lists = [evalg.database.query.get_or_create(
        db_session, ElectionList, **x) for x in data]

    for election_list in election_lists:
        db_session.add(election_list)

    # We need to flush here to generate ids for the election lists
    db_session.flush()

    # Add candidates to first election list
    for candidate in candidate_data:
        candidate['list_id'] = str(election_lists[0].id)

    # Add team candidates to the second election list
    for candidate in candidate_team_data:
        candidate['list_id'] = str(election_lists[1].id)

    candidates = [evalg.database.query.get_or_create(
        db_session, Candidate, **x) for x in candidate_data]
    for candidate in candidates:
        db_session.add(candidate)

    team_candidates = [evalg.database.query.get_or_create(
        db_session, Candidate, **x) for x in candidate_team_data]
    for candidate in team_candidates:
        db_session.add(candidate)

    db_session.flush()

    return {str(x.id): x for x in election_lists}
