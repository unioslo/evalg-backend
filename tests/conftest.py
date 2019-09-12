import datetime
import pytest
import random

import evalg.database.query

from evalg import create_app, db
from evalg.authentication import user
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer
from evalg.models.candidate import Candidate
from evalg.models.ballot import Envelope
from evalg.models.votes import Vote
from evalg.models.election import ElectionGroup, Election
from evalg.models.election_group_count import ElectionGroupCount
from evalg.models.election_list import ElectionList
from evalg.models.election_result import ElectionResult
from evalg.models.group import Group
from evalg.models.group import GroupMembership
from evalg.models.ou import OrganizationalUnit
from evalg.models.person import Person, PersonExternalId
from evalg.models.pollbook import PollBook
from evalg.models.voter import Voter
from evalg.proc.vote import ElectionVotePolicy

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
        FEIDE_MOCK_LOGIN_AS = 'a6733d24-8987-44b6-8cd0-308030710aa2'
        FEIDE_MOCK_DATA = {
            'client_id': 'f7a0afcd-2b9a-461d-b82c-816d637b68da',
            'users': {
                'a6733d24-8987-44b6-8cd0-308030710aa2': {
                    'id': 'a6733d24-8987-44b6-8cd0-308030710aa2',
                    'sec': {
                        'feide': ('baz@example.org',),
                        'nin': ('12128812337',),
                    },
                    'dp_user_info': {
                        'user': {
                            'name': 'Baz Baz',
                            'email': 'baz@example.org',
                        },
                        'audience': 'mock',
                    },
                },
            },

        }
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

    This fixture is expected by `pytest-flask-sqlalchemy`
    """
    return database


@pytest.yield_fixture(scope='function')
def logged_in_user(db_session, app, config):
    with app.test_request_context():
        app.preprocess_request()
        yield user


@pytest.fixture
def election_keys_foo():
    return {
        'public': 'bO1pw6/Bslji0XvXveSuVbe4vp93K1DcpqYgIxRhYAs=',
        'private': 'FTVBa1ThHyKfE/LRYkRZ+79NyQw17PuD7gcD/ViJzYE=',
    }


@pytest.fixture
def election_vote_policy_foo(db_session):
    return ElectionVotePolicy(db_session)


@pytest.fixture
def make_ou(db_session):

    def make_ou(name):
        data = {
            'name': {
                'nb': 'nb: {0}'.format(name),
                'nn': 'nn: {0}'.format(name),
                'en': 'en: {0}'.format(name),
            },
            'external_id': '{0}'.format(name)
        }

        ou = evalg.database.query.get_or_create(
            db_session, OrganizationalUnit, **data)
        db_session.add(ou)
        db_session.flush()
        return ou

    return make_ou


@pytest.fixture
def make_election_group(db_session, election_keys_foo, make_person_principal,
                        logged_in_user, make_role):
    """
    Election group fixture.
    """

    def make_election_group(name, announced_at=None, published_at=None,
                            admin=False):
        data = {
            'name': {
                'nb': name,
                'en': name,
            },
            'type': 'single_election',
            'description': {
                'nb': 'Description foo',
                'en': 'Description foo',
            },
            'announced_at': announced_at,
            'published_at': published_at,
            'public_key': election_keys_foo['public'],
        }

        election_group = evalg.database.query.get_or_create(
            db_session, ElectionGroup, **data)
        election_group.publish()
        election_group.announce()

        db_session.add(election_group)
        db_session.flush()
        if admin:
            person_principal = make_person_principal(logged_in_user.person)
            make_role(election_group, person_principal)
        return election_group

    return make_election_group


@pytest.fixture
def make_election_group_from_template(db_session, make_ou):
    def make_election_group_from_template(ou_name, template_name,
                                          current_user):

        ou = make_ou(name=ou_name)

        election_group = evalg.proc.election.make_group_from_template(
            db_session, template_name, ou)
        current_user_principal = evalg.proc.authz.get_or_create_principal(
            db_session,
            principal_type='person',
            person_id=current_user.person.id)
        evalg.proc.authz.add_election_group_role(
            session=db_session,
            election_group=election_group,
            principal=current_user_principal,
            role_name='admin')
        db_session.commit()

        return election_group

    return make_election_group_from_template


@pytest.fixture
def election_group_baz(make_election_group):
    return make_election_group('Baz', admin=False)


@pytest.fixture
def election_group_foo(make_election_group):
    return make_election_group('Election group foo fixture',  admin=True)


@pytest.fixture
def make_election(db_session, election_group_foo):
    def make_election(name, election_group=None):
        if not election_group:
            election_group = election_group_foo
        data = {
            'name': {
                'nb': name,
                'en': name,
            },
            'description': {
                'nb': 'Description {0}'.format(name),
                'en': 'Description {0}'.format(name),
            },
            'group_id': election_group.id,
            'start': datetime.datetime.now(datetime.timezone.utc),
            'end': datetime.datetime.now(
                datetime.timezone.utc) + datetime.timedelta(days=1)
        }
        election = evalg.database.query.get_or_create(
            db_session, Election, **data)
        db_session.add(election)
        db_session.flush()
        return election

    return make_election


@pytest.fixture
def election_foo(make_election):
    """Election fixture."""
    return make_election('Election foo')


election_list_data = {
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
}


@pytest.fixture
def election_list_pref_foo(db_session, election_foo):
    """Election list fixture, with candidates."""
    election_list_data["election_id"] = election_foo.id

    election_list = evalg.database.query.get_or_create(
        db_session, ElectionList, **election_list_data)

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


pref_candidates_data = [
    {
        "name": "Peder Aas",
        "meta": {
            "gender": "Male"
        },
    },
    {
        "name": "Marte Kirkerud",
        "meta": {
            "gender": "female"
        },
    },
]


@pytest.fixture
def pref_candidates_foo(db_session, election_list_pref_foo):
    [x.update({'list_id': election_list_pref_foo.id}) for x in
     pref_candidates_data]
    candidates = [evalg.database.query.get_or_create(
        db_session, Candidate, **x) for x in pref_candidates_data]
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
def make_pollbook(db_session, election_foo):
    def make_pollbook(name, election=None):
        if not election:
            election = election_foo

        data = {
            "name": {
                "nb": name,
                "en": name,
            },
            "election_id": election.id,
        }
        pollbook = evalg.database.query.get_or_create(
            db_session, PollBook, **data)
        db_session.add(pollbook)
        db_session.flush()
        return pollbook

    return make_pollbook


@pytest.fixture
def pollbook_foo(db_session, make_pollbook):
    return make_pollbook('Poolbook Foo')


@pytest.fixture
def make_person(db_session):
    def make_person(display_name, email, nin=None):
        data = {
            'email': email,
            'display_name': display_name,
        }
        identifiers = [
            {
                'id_type': 'feide_id',
                'id_value': email,
            },
            {
                'id_type': 'uid',
                'id_value': email.split('@')[0],
            },
            {
                'id_type': 'nin',
                'id_value': nin or ''.join([str(random.randint(0, 9)) for _ in
                                     range(0, 10)]),
            },
        ]
        person = evalg.database.query.get_or_create(db_session, Person, **data)
        for identifier in identifiers:
            id_obj = evalg.database.query.get_or_create(
                db_session, PersonExternalId, **identifier)
            person.identifiers.append(id_obj)
        db_session.add(person)
        db_session.flush()
        return person

    return make_person


@pytest.fixture
def persons(db_session, make_person):
    """
    Returns all persons in the test database.

    We add a couple if the database is empty.
    """
    persons = Person.query.all()
    if len(persons) <= 1:
        persons = [
            make_person('Foo Foo', 'foo@example.org', nin='12128812345'),
            make_person('Bar Bar', 'bar@example.org')
        ]

    return {str(x.id): x for x in persons}


@pytest.fixture
def person_foo(persons):
    for x in persons.values():
        if x.email == 'foo@example.org':
            return x
    assert False


@pytest.fixture
def make_group(db_session):
    """Returns a method that create new groups."""
    def make_group(name):
        data = {
            'name': name,
        }
        group = evalg.database.query.get_or_create(db_session, Group, **data)
        db_session.add(group)
        db_session.flush()
        return group
    return make_group


@pytest.fixture
def make_group_membership(db_session):
    """Returns a method for adding persons to groups."""
    def make_group_membership(group, person):
        data = {
            'group_id': group.id,
            'person_id': person.id,
        }
        membership = evalg.database.query.get_or_create(
            db_session,
            GroupMembership,
            **data)
        db_session.add(membership)
        db_session.flush()
        return membership
    return make_group_membership


@pytest.fixture
def make_person_publisher(db_session, global_roles, make_group_membership):
    """Make a giver person a publisher."""
    def make_person_publisher(person):
        publisher_group = global_roles['publisher']['group']
        return make_group_membership(publisher_group, person)
    return make_person_publisher


@pytest.fixture
def make_person_principal(db_session):
    def make_person_principal(person, principal_type='person'):
        return evalg.proc.authz.get_or_create_principal(
            db_session,
            principal_type=principal_type,
            person_id=person.id)

    return make_person_principal


@pytest.fixture
def make_group_principal(db_session):
    """Returns a method for creating group principals."""
    def make_group_principal(group):
        return evalg.proc.authz.get_or_create_principal(
            db_session,
            principal_type='group',
            group_id=group.id,
        )
    return make_group_principal


@pytest.fixture
def make_role(db_session):
    def make_role(election_group,
                  principal,
                  role_name='admin',
                  global_role=False):
        return evalg.proc.authz.add_election_group_role(
            session=db_session,
            election_group=election_group,
            principal=principal,
            role_name=role_name)

    return make_role


@pytest.fixture
def global_roles(db_session, make_group, make_group_principal):
    """Create the global roles and groups."""
    publisher_group = make_group('publisher')
    global_admin_group = make_group('global_admin')
    publisher_principal = make_group_principal(publisher_group)
    global_admin_principal = make_group_principal(global_admin_group)
    publisher_role = evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=None,
        principal=publisher_principal,
        role_name='publisher',
        global_role=True
    )
    global_admin_role = evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=None,
        principal=global_admin_principal,
        role_name='global_admin',
        global_role=True
    )
    return {
        'publisher': {
            'group': publisher_group,
            'principal': publisher_principal,
            'role': publisher_role
        },
        'global_admin': {
            'group': global_admin_group,
            'principal': global_admin_principal,
            'role': global_admin_role
        }
    }


@pytest.fixture
def make_pollbook_voter(db_session, person_foo, pollbook_foo):
    def make_pollbook_voter(person=None, pollbook=None):

        if not person:
            person = person_foo
        if not pollbook:
            pollbook = pollbook_foo

        data = {
            'id_type': person.identifiers[0].id_type,
            'id_value': person.identifiers[0].id_value,
            'pollbook_id': pollbook.id,
            'self_added': False,
            'reviewed': False,
            'verified': True,
        }

        pollbook_voter = evalg.database.query.get_or_create(
            db_session, Voter, **data)
        db_session.add(pollbook_voter)
        db_session.flush()
        return pollbook_voter

    return make_pollbook_voter


@pytest.fixture
def pollbook_voter_foo(db_session, make_pollbook_voter):
    return make_pollbook_voter()


@pytest.fixture
def election_pref_vote(pref_candidates_foo):
    ballot_data = {
        'voteType': 'prefElecVote',
        'isBlankVote': False,
        'rankedCandidateIds': [str(x.id) for x in pref_candidates_foo]
    }

    return ballot_data


@pytest.fixture
def make_pollbook_vote(db_session, election_pref_vote,
                       pollbook_voter_foo,
                       election_vote_policy_foo):
    def make_pollbook_vote(pollbook_voter=None, ballot_data=None):
        if not ballot_data:
            ballot_data = election_pref_vote

        if not pollbook_voter:
            pollbook_voter = pollbook_voter_foo

        return election_vote_policy_foo.add_vote(pollbook_voter,
                                                 ballot_data.copy())

    return make_pollbook_vote


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
    # TODO: Dummy result, change to use a "real" election result
    data = {
        'election_id': election_foo.id,
        'election_group_count_id': election_group_count_foo.id,
        'election_protocol': {'test123': '123123'},
        'ballots': [{'vote': 'test'}, {'vote': 'test2'}],
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


@pytest.fixture
def election_group_bar(make_election_group):
    return make_election_group(
        'Bar',
        announced_at=(datetime.datetime.now(datetime.timezone.utc) -
                      datetime.timedelta(days=3)),
        published_at=(datetime.datetime.now(datetime.timezone.utc) -
                      datetime.timedelta(days=3)),
        admin=True
    )


@pytest.fixture
def election_bar(db_session, election_group_bar):
    data = {
        'name': {
            'nb': 'Valg av bar',
            'en': 'Election of bar',
        },
        'description': {
            'nb': 'Description bar',
            'en': 'Description bar',
        },
        'meta': {
            'candidate_rules': {'candidate_gender': True,
                                'seats': 1},
            'counting_rules': {'method': 'uio_stv',
                               'affirmative_action': ['gender_40']},
        },
        'active': True,
        'group_id': election_group_bar.id,
        'start': (datetime.datetime.now(datetime.timezone.utc) -
                  datetime.timedelta(days=2)),
        'end': (datetime.datetime.now(datetime.timezone.utc) -
                datetime.timedelta(days=1)),

    }
    election = evalg.database.query.get_or_create(
        db_session, Election, **data)
    db_session.add(election)
    db_session.flush()
    return election


@pytest.fixture
def election_list_pref_bar(db_session, election_bar):
    election_list_data['election_id'] = election_bar.id

    election_list = evalg.database.query.get_or_create(
        db_session, ElectionList, **election_list_data)

    db_session.add(election_list)
    db_session.flush()
    return election_list


@pytest.fixture
def pref_candidates_bar(db_session, election_list_pref_bar):
    [x.update({'list_id': election_list_pref_bar.id}) for x in
     pref_candidates_data]
    candidates = [evalg.database.query.get_or_create(
        db_session, Candidate, **x) for x in pref_candidates_data]
    for candidate in candidates:
        db_session.add(candidate)
        election_list_pref_bar.candidates.append(candidate)
    db_session.flush()
    return candidates


@pytest.fixture
def pollbook_bar(db_session, election_bar):
    data = {
        "name": {
            "nb": "Pollbook bar",
            "en": "Pollbook bar",
        },
        "election_id": election_bar.id,
    }

    pollbook = evalg.database.query.get_or_create(db_session,
                                                  PollBook,
                                                  **data)

    db_session.add(pollbook)
    db_session.flush()
    return pollbook


@pytest.fixture
def pollbook_voter_bar(db_session, person_foo, pollbook_bar):
    person = person_foo

    data = {
        'id_type': person.identifiers[0].id_type,
        'id_value': person.identifiers[0].id_value,
        'pollbook_id': pollbook_bar.id,
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
def envelope_bar(db_session, config, pref_candidates_bar, election_keys_foo,
                 pollbook_bar):
    ballot_serializer = Base64NaClSerializer(
        election_public_key=election_keys_foo['public'],
        backend_private_key=getattr(config, 'BACKEND_PRIVATE_KEY'),
        envelope_padded_len=getattr(config, 'ENVELOPE_PADDED_LEN'),
    )
    ballot_data = {
        'pollbookId': str(pollbook_bar.id),
        'rankedCandidateIds': [str(candidate.id) for candidate in
                               pref_candidates_bar]
    }
    data = {
        'envelope_type': 'base64-nacl',
        'ballot_type': 'test_ballot',
        'ballot_data': ballot_serializer.serialize(ballot_data)
    }
    envelope = evalg.database.query.get_or_create(
        db_session,
        Envelope,
        **data
    )
    db_session.add(envelope)
    db_session.flush()
    return envelope


@pytest.fixture
def vote_bar(db_session, pollbook_voter_bar, envelope_bar):
    data = {
        'voter_id': pollbook_voter_bar.id,
        'ballot_id': envelope_bar.id,

    }
    vote = evalg.database.query.get_or_create(
        db_session,
        Vote,
        **data
    )
    db_session.add(vote)
    db_session.flush()
    return vote


@pytest.fixture
def make_full_election(make_election_group, make_election, make_pollbook,
                       make_person, make_pollbook_voter, make_pollbook_vote):
    def make_full_election(name, nr_of_elections=2, pollboks_per_election=1,
                           voters_per_pollbook=1):
        election_group = make_election_group('Test election group', admin=True)

        elections = [make_election('{0} election {1}'.format(name, x),
                                   election_group=election_group) for x in
                     range(1, nr_of_elections + 1)]

        pollbooks = {}
        pollbook_voters = {}
        persons_all = []
        voters_all = []

        for election in elections:

            pollbooks[str(election.id)] = ([make_pollbook(
                '{0} pollbook {1}'.format(election.name, x),
                election=election) for x in range(0, pollboks_per_election)])

            for pollbook in pollbooks[str(election.id)]:
                p = [make_person('{0} test person {1}'.format(
                    pollbook.name, x), '{0}-{1}@example.org'.format(
                    name, x)) for x in range(0, voters_per_pollbook)]
                persons_all.extend(p)
                v = [make_pollbook_voter(x, pollbook) for x in p]

                voters_all.extend(v)
                pollbook_voters[str(pollbook.id)] = v

        # TODO create more votes.
        votes = [make_pollbook_vote(pollbook_voter=voters_all[0])]

        return {
            'election_group': election_group,
            'elections': elections,
            'pollbooks': pollbooks,
            'pollbook_voters': pollbook_voters,
            'persons_all': persons_all,
            'voters_all': voters_all,
            'votes': votes,
        }

    return make_full_election
