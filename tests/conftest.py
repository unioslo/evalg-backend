import datetime
import json
import pytest

import evalg.database.query
from evalg import create_app, db
from evalg.models.candidate import Candidate
from evalg.models.election import ElectionGroup, Election
from evalg.models.election_group_count import ElectionGroupCount
from evalg.models.election_list import ElectionList
from evalg.models.election_result import ElectionResult
from evalg.models.person import Person, PersonExternalId
from evalg.models.pollbook import PollBook
from evalg.models.voter import Voter

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
        BACKEND_PRIVATE_KEY = 'nnQjcDrXcIc8mpHabme8j7/xPBWqIkPElM8KtAJ4vgc='
        BACKEND_PUBLIC_KEY = 'KLUDKkCPrAEcK9SrYDyMsrLEShm6axS9uSG/sOfibCA='
        ENVELOPE_TYPE = 'base64-nacl'
        ENVELOPE_PADDED_LEN = 1000

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
def election_keys_foo():
    return {
        'public': 'bO1pw6/Bslji0XvXveSuVbe4vp93K1DcpqYgIxRhYAs=',
        'private': 'FTVBa1ThHyKfE/LRYkRZ+79NyQw17PuD7gcD/ViJzYE=',
    }


@pytest.fixture
def election_group_foo(db_session, election_keys_foo):
    """
    Election group fixture.

    """
    data = {
        'name': {
            'nb': 'Foo',
            'en': 'Foo',
        },
        'type': 'single_election',
        'description': {
            'nb': 'Description foo',
            'en': 'Description foo',
        },
        'public_key': election_keys_foo['public'],

    }
    election_group = evalg.database.query.get_or_create(
        db_session, ElectionGroup, **data)
    election_group.publish()
    election_group.announce()
    db_session.add(election_group)
    db_session.flush()
    return election_group


@pytest.fixture
def election_foo(db_session, election_group_foo):
    """Election fixture."""

    data = {
        'name': {
            'nb': 'Valg av foo',
            'en': 'Election of foo',
        },
        'type': 'single_election',
        'description': {
            'nb': 'Description foo',
            'en': 'Description foo',
        },
        'group_id': election_group_foo.id,
        'start': datetime.datetime.now(datetime.timezone.utc),
        'end': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }
    election = evalg.database.query.get_or_create(
        db_session, Election, **data)
    db_session.add(election)
    db_session.flush()
    return election


@pytest.fixture
def election_list_pref_foo(db_session, election_foo):
    """Election list fixture, with candidates."""
    data = {
        "name": {
            "nb": "Vitenskapelig ansatte",
            "nn": "Vitskapeleg tilsette",
            "en": "Academic staff",
        },
        "description": {
            "nb": "Vitenskapelig ansatte",
            "nn": "Vitskapeleg tilsette",
            "en": "Academic staff"
        },
        "information_url": "https://uio.no",
        "election_id": election_foo.id,
    }

    election_list = evalg.database.query.get_or_create(
        db_session, ElectionList, **data)

    db_session.add(election_list)
    db_session.flush()
    return election_list


@pytest.fixture
def election_list_team_pref_foo(db_session, election_foo):
    """Election list fixture, with candidates."""
    data = {
        "name": {
            "nb": "Vitenskapelig ansatte",
            "nn": "Vitskapeleg tilsette",
            "en": "Academic staff",
        },
        "description": {
            "nb": "Vitenskapelig ansatte",
            "nn": "Vitskapeleg tilsette",
            "en": "Academic staff"
        },
        "information_url": "https://uio.no",
        "election_id": election_foo.id,
    }

    election_list = evalg.database.query.get_or_create(
        db_session, ElectionList, **data)

    db_session.add(election_list)
    db_session.flush()
    return election_list


@pytest.fixture
def pref_candidates_foo(db_session, election_list_pref_foo):
    data = [
        {
            "name": "Peder Aas",
            "meta": {
                "gender": "Male"
            },
            "list_id": election_list_pref_foo.id,
        },
        {
            "name": "Marte Kirkerud",
            "meta": {
                "gender": "female"
            },
            "list_id": election_list_pref_foo.id,
        },
    ]
    candidates = [evalg.database.query.get_or_create(
        db_session, Candidate, **x) for x in data]
    for candidate in candidates:
        db_session.add(candidate)
        election_list_pref_foo.candidates.append(candidate)
    db_session.flush()
    return candidates


@pytest.fixture
def team_pref_candidates_foo(db_session, election_list_team_pref_foo):
    data = [
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
            "user_cumulated": False,
            "list_id": election_list_team_pref_foo.id,
        },
    ]
    candidates = [evalg.database.query.get_or_create(
        db_session, Candidate, **x) for x in data]
    for candidate in candidates:
        db_session.add(candidate)
        election_list_team_pref_foo.candidates.append(candidate)
    db_session.flush()
    return candidates


@pytest.fixture
def pollbook_foo(db_session, election_foo):
    data = {
        "name": {
            "nb": "Pollbook foo",
            "en": "Pollbook foo",
        },
        "election_id": election_foo.id,
    }
    pollbook = evalg.database.query.get_or_create(
        db_session, PollBook, **data)
    db_session.add(pollbook)
    db_session.flush()

    return pollbook


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
def pollbook_voter_foo(db_session, persons, pollbook_foo):
    person = next(iter(persons.values()))

    data = {
        'id_type': person.identifiers[0].id_type,
        'id_value': person.identifiers[0].id_value,
        'pollbook_id': pollbook_foo.id,
        'self_added': False,
        'reviewed': False,
        'verified': True,
    }

    pollbook_voter = evalg.database.query.get_or_create(
        db_session, Voter, **data)

    db_session.add(pollbook_voter)
    db_session.flush()

    return pollbook_voter


@pytest.fixture
def election_group_count_foo(db_session, election_group_foo):

    data = {
        'group_id': election_group_foo.id,
    }

    election_group_count = evalg.database.query.get_or_create(
        db_session,
        ElectionGroupCount,
        **data,
    )

    db_session.add(election_group_count)
    db_session.flush()

    return election_group_count


@pytest.fixture
def election_result_foo(db_session, election_foo, election_group_count_foo):

    data = {
        'election_id': election_foo.id,
        'election_group_count_id': election_group_count_foo.id,
        'path_to_election_protocol': '/test/123',
        'votes': {
            'votes': [{'vote': 'test'}, {'vote': 'test2'}]
        },
        'result': {"winner": "test"}
    }

    election_result = evalg.database.query.get_or_create(
        db_session,
        ElectionResult,
        **data,
    )

    db_session.add(election_result)
    db_session.flush()

    return election_result
