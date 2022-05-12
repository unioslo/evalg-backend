import datetime
import string
import random
from typing import Callable

import pytest

import nacl.encoding
import nacl.public

import evalg.database.query

from evalg import create_app, db
from evalg.authentication import user
from evalg.models.candidate import Candidate
from evalg.models.election import ElectionGroup, Election
from evalg.models.election_list import ElectionList
from evalg.models.group import Group
from evalg.models.group import GroupMembership
from evalg.models.privkeys_backup import MasterKey
from evalg.models.ou import OrganizationalUnit
from evalg.models.person import Person, PersonExternalId
from evalg.models.pollbook import Pollbook
from evalg.proc.pollbook import ElectionVoterPolicy
from evalg.proc.vote import ElectionVotePolicy

pytest_plugins = ("pytest-flask-sqlalchemy", "celery.contrib.pytest")


@pytest.fixture(scope="session")
def config():
    """Application config."""

    class Config(object):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        AUTH_ENABLED = True
        AUTH_METHOD = "feide_mock"
        FEIDE_BASIC_REQUIRE = False
        FEIDE_MOCK_LOGIN_AS = "a6733d24-8987-44b6-8cd0-308030710aa2"
        FEIDE_MOCK_DATA = {
            "client_id": "f7a0afcd-2b9a-461d-b82c-816d637b68da",
            "users": {
                "a6733d24-8987-44b6-8cd0-308030710aa2": {
                    "id": "a6733d24-8987-44b6-8cd0-308030710aa2",
                    "sec": {
                        "feide": ("baz@example.org",),
                        "nin": ("12128812337",),
                    },
                    "dp_user_info": {
                        "user": {
                            "name": "Baz Baz",
                            "email": "baz@example.org",
                        },
                        "audience": "mock",
                    },
                },
            },
        }
        BACKEND_PRIVATE_KEY = "nnQjcDrXcIc8mpHabme8j7/xPBWqIkPElM8KtAJ4vgc="
        BACKEND_PUBLIC_KEY = "KLUDKkCPrAEcK9SrYDyMsrLEShm6axS9uSG/sOfibCA="
        ENVELOPE_TYPE = "base64-nacl"
        ENVELOPE_PADDED_LEN = 1000
        CELERY_BROKER_URL = "redis://"

    return Config()


@pytest.yield_fixture(scope="function")
def database(app, request):
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()


@pytest.fixture(scope="session")
def app(config):
    app = create_app(config=config)
    return app


@pytest.fixture(scope="function")
def _db(app, database):
    """
    Provide the transactional fixtures with access to the database via a
    Flask-SQLAlchemy database connection.

    This fixture is expected by `pytest-flask-sqlalchemy`
    """
    return database


@pytest.yield_fixture(scope="function")
def logged_in_user(db_session, app, config):
    with app.test_request_context():
        app.preprocess_request()
        yield user


@pytest.fixture(scope="session")
def celery_config():
    return {"broker_url": "redis://", "result_backend": "redis://"}


@pytest.fixture
def election_keys():
    return {
        "public": "bO1pw6/Bslji0XvXveSuVbe4vp93K1DcpqYgIxRhYAs=",
        "private": "FTVBa1ThHyKfE/LRYkRZ+79NyQw17PuD7gcD/ViJzYE=",
    }


@pytest.fixture
def election_vote_policy_generator(db_session):
    def election_vote_policy(voter_id):
        return ElectionVotePolicy(db_session, voter_id)

    return election_vote_policy


@pytest.fixture
def persons(db_session, person_generator):
    """
    Returns all persons in the test database.

    We add a couple if the database is empty.
    """
    persons = Person.query.all()
    if len(persons) <= 1:
        persons = [
            person_generator(
                "Foo Foo",
                "foo@example.org",
                ids={"nin": "12128812345", "feide_id": "foo@example.org"},
            ),
            person_generator("Bar Bar", "bar@example.org"),
        ]

    return {str(x.id): x for x in persons}


@pytest.fixture
def group_generator():
    """Returns a method that create new groups."""

    def group_generator(db_session, name):
        data = {
            "name": name,
        }
        group = evalg.database.query.get_or_create(db_session, Group, **data)
        db_session.add(group)
        db_session.flush()
        return group

    return group_generator


@pytest.fixture
def make_group_membership():
    """Returns a method for adding persons to groups."""

    def make_group_membership(db_session, group, person):
        data = {
            "group_id": group.id,
            "person_id": person.id,
        }
        membership = evalg.database.query.get_or_create(
            db_session, GroupMembership, **data
        )
        db_session.add(membership)
        db_session.flush()
        return membership

    return make_group_membership


@pytest.fixture
def make_person_publisher(global_roles, make_group_membership):
    """Make a giver person a publisher."""

    def make_person_publisher(db_session, person):
        publisher_group = global_roles["publisher"]["group"]
        return make_group_membership(db_session, publisher_group, person)

    return make_person_publisher


@pytest.fixture
def make_person_principal(db_session):
    def make_person_principal(person, principal_type="person"):
        return evalg.proc.authz.get_or_create_principal(
            db_session, principal_type=principal_type, person_id=person.id
        )

    return make_person_principal


@pytest.fixture
def make_group_principal(db_session):
    """Returns a method for creating group principals."""

    def make_group_principal(group):
        return evalg.proc.authz.get_or_create_principal(
            db_session,
            principal_type="group",
            group_id=group.id,
        )

    return make_group_principal


@pytest.fixture
def make_role(db_session):
    def make_role(election_group, principal, role_name="admin", global_role=False):
        return evalg.proc.authz.add_election_group_role(
            session=db_session,
            election_group=election_group,
            principal=principal,
            role_name=role_name,
        )

    return make_role


@pytest.fixture
def grant_for_person_generator(db_session):
    def grant_for_person_generator(person, election_group):
        feide_id = next(i for i in person.identifiers if i.id_type == "feide_id")

        principal = evalg.proc.authz.get_or_create_principal(
            session=db_session,
            principal_type="person_identifier",
            id_type=feide_id.id_type,
            id_value=feide_id.id_value,
        )
        grant = evalg.proc.authz.add_election_group_role(
            session=db_session,
            election_group=election_group,
            principal=principal,
            role_name="admin",
        )
        db_session.commit()
        return grant

    return grant_for_person_generator


@pytest.fixture
def global_roles(db_session, group_generator, make_group_principal):
    """Create the global roles and groups."""
    publisher_group = group_generator(db_session, "publisher")
    global_admin_group = group_generator(db_session, "global_admin")
    publisher_principal = make_group_principal(publisher_group)
    global_admin_principal = make_group_principal(global_admin_group)
    publisher_role = evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=None,
        principal=publisher_principal,
        role_name="publisher",
        global_role=True,
    )
    global_admin_role = evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=None,
        principal=global_admin_principal,
        role_name="global_admin",
        global_role=True,
    )
    return {
        "publisher": {
            "group": publisher_group,
            "principal": publisher_principal,
            "role": publisher_role,
        },
        "global_admin": {
            "group": global_admin_group,
            "principal": global_admin_principal,
            "role": global_admin_role,
        },
    }


def _ballot_data_generator(
    pollbook, vote_type="prefElectVote", blank_vote=False, candidates=None
):
    """Ballot data generator used to crate fixtures."""
    if blank_vote and (candidates and len(candidates) != 0):
        raise ValueError("Ballot can't be both blank and have " "candidates.")

    if not candidates or len(candidates) == 0:
        blank_vote = True
        candidates = []

    ballot_data = {
        "voteType": vote_type,
        "isBlankVote": blank_vote,
        "pollbookId": str(pollbook.id),
        "rankedCandidateIds": [str(x.id) for x in candidates],
    }
    return ballot_data


@pytest.fixture
def ballot_data_generator():
    def ballot_data_generator(
        pollbook, vote_type="prefElectVote", blank_vote=False, candidates=None
    ):

        return _ballot_data_generator(
            pollbook, vote_type=vote_type, blank_vote=blank_vote, candidates=candidates
        )

    return ballot_data_generator


@pytest.fixture
def master_key():
    def master_key(db_session):
        """Master key fixture."""
        private_key = nacl.public.PrivateKey.generate()
        pubkey = private_key.public_key.encode(nacl.encoding.Base64Encoder)
        master_key = MasterKey(
            description="Master key for testing", public_key=pubkey.decode()
        )
        db_session.add(master_key)
        db_session.flush()
        return private_key, master_key

    return master_key


@pytest.fixture
def ou_generator(db_session):
    """Generate test OUs."""

    def ou_generator():
        """OU test fixture."""
        name_rand = "".join(random.choices(string.ascii_lowercase, k=10))
        name = "unit-{}".format(name_rand)

        data = {
            "name": {
                "nb": "nb: {0}".format(name),
                "nn": "nn: {0}".format(name),
                "en": "en: {0}".format(name),
            },
            "external_id": "{0}".format(name),
        }
        ou = evalg.database.query.get_or_create(db_session, OrganizationalUnit, **data)
        db_session.add(ou)
        db_session.flush()
        return ou

    return ou_generator


def _person_generator(db_session, display_name=None, email=None, ids=None):
    """Generate persons used by fixtures."""
    if not display_name:
        rand_gn = "".join(random.choices(string.ascii_lowercase, k=8))
        rand_cn = "".join(random.choices(string.ascii_lowercase, k=8))
        display_name = "{} {}".format(rand_gn, rand_cn)

    if not email:
        rand_local = "".join(random.choices(string.ascii_lowercase, k=8))
        email = "{}@example.org".format(rand_local)

    if not ids:
        ids = {}

    rand_slug = "".join(random.choices(string.ascii_lowercase, k=10))
    if "uid" not in ids:
        ids["uid"] = rand_slug

    if "feide_id" not in ids:
        ids["feide_id"] = "{}@uio.no".format(rand_slug)

    if "nin" not in ids:
        ids["nin"] = "".join([str(random.randint(0, 9)) for _ in range(0, 10)])

    data = {
        "display_name": display_name,
        "email": email,
    }
    identifiers = [
        {
            "id_type": "feide_id",
            "id_value": ids["feide_id"],
        },
        {
            "id_type": "uid",
            "id_value": ids["uid"],
        },
        {
            "id_type": "nin",
            "id_value": ids["nin"],
        },
    ]
    person = Person(**data)
    new_ids = []
    for identifier in identifiers:
        id_obj = PersonExternalId(**identifier)
        new_ids.append(id_obj)
    person.identifiers = new_ids
    db_session.add(person)
    db_session.flush()
    return person


@pytest.fixture
def person_generator(db_session):
    def person_generator(display_name=None, email=None, ids=None):
        return _person_generator(
            db_session, display_name=display_name, email=email, ids=ids
        )

    return person_generator


def pollbook_generator(
    db_session,
    election,
    name=None,
    with_self_added_voters=False,
    nr_of_voters=10,
    weight=None,
    voters_with_votes=False,
):
    """Generate pollbooks used by fixtures."""
    if not name:
        name_rand = "".join(random.choices(string.ascii_lowercase, k=10))
        name = "poolbook-{}".format(name_rand)

    data = {
        "name": {
            "nb": name,
            "en": name,
        },
        "election_id": election.id,
    }

    if weight:
        data["weight"] = weight

    pollbook = evalg.database.query.get_or_create(db_session, Pollbook, **data)
    db_session.add(pollbook)
    db_session.flush()

    self_added_status = [False for _ in range(nr_of_voters)]

    if with_self_added_voters:
        self_added_status[0] = True
        self_added_status[1] = True

    for self_added in self_added_status:
        person = _person_generator(db_session)
        voter_policy = ElectionVoterPolicy(db_session)
        voter = voter_policy.add_voter(pollbook, person, self_added=self_added)
        db_session.add(voter)

    db_session.flush()

    if voters_with_votes:
        # Add votes to half of the voters
        for voter in pollbook.voters[: len(pollbook.voters) // 2]:
            election_vote_policy = ElectionVotePolicy(db_session, voter.id)
            election_vote_policy.add_vote(
                _ballot_data_generator(pollbook, candidates=election.candidates)
            )

    return pollbook


def candidate_generator(db_session, candidate_type, candidate_list, gender=None):

    if candidate_type == "single":
        if gender:
            meta = {"gender": gender}
        else:
            meta = {"gender": random.choice(["male", "female"])}
    elif candidate_type == "single_team":
        meta = {"co_candidates": [{"name": "test"}]}
    elif candidate_type == "party_list":
        raise NotImplementedError
    else:
        raise NotImplementedError

    name_rand = "".join(random.choices(string.ascii_lowercase, k=10))
    candidate_name = "candidate-{0}".format(name_rand)
    candidate = Candidate(
        name=candidate_name,
        meta=meta,
        list_id=candidate_list.id,
        information_url="www.uio.no",
    )
    db_session.add(candidate)
    db_session.flush()
    return candidate


def list_election_generator(
    db_session,
    election_group,
    running=False,
    countable=False,
) -> Callable[..., Election]:
    """Generate an election."""
    if running and countable:
        raise ValueError("Election can't be running and countable at the " "same time")

    nr_of_elections = 1
    election_meta = {
        "candidate_type": "party_list",
        "candidate_rules": {"seats": 30},
        "ballot_rules": {
            "delete_candidate": True,
            "cumulate": True,
            "alter_priority": True,
            "number_of_votes": "seats",
            "other_list_candidate_votes": True,
            "voting": "list",
        },
        "counting_rules": {
            "method": "sainte_lague",
            "first_divisor": 1,
            "precumulate": 1,
            "list_votes": "seats",
            "other_list_candidate_votes": True,
        },
    }

    # "method": election_group.meta["counting_rules"]["method"],
    # In future, running, in past
    if running:
        start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=1
        )
        end = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    elif countable:
        start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=4
        )
        end = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
    else:
        # Default is elections in the future
        start = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=1
        )
        end = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)

    elections = []
    for i in range(nr_of_elections):
        name_rand = "".join(random.choices(string.ascii_lowercase, k=10))
        election_name = "election-{}".format(name_rand)

        data = {
            "name": {
                "nb": election_name,
                "en": election_name,
            },
            "description": {
                "nb": "Description {}".format(i),
                "en": "Description {}".format(i),
            },
            "group_id": election_group.id,
            "start": start,
            "end": end,
            "active": True,
            "mandate_period_start": (
                datetime.date.today() + datetime.timedelta(days=30)
            ),
            "mandate_period_end": (
                datetime.date.today() + datetime.timedelta(weeks=200)
            ),
            "meta": election_meta,
        }
        election = evalg.database.query.get_or_create(db_session, Election, **data)
        db_session.add(election)
        db_session.flush()

        election_list = ElectionList(
            election_id=str(election.id),
            name={"nb": election_name, "en": election_name},
        )
        db_session.add(election_list)
        election.lists = [election_list]

        election.pollbooks = [
            pollbook_generator(
                db_session,
                election,
                weight=100,
            )
        ]
        db_session.flush()
        elections.append(election)
    return elections


def new_elections_generator(
    db_session,
    election_group,
    candidates_per_pollbook=1,
    nr_of_seats=1,
    nr_of_substitutes=2,
    running=False,
    countable=False,
    with_self_added_voters=False,
    voters_with_votes=False,
    multiple=False,
    nr_of_votes="all",
):
    """Generate an election."""
    if running and countable:
        raise ValueError("Election can't be running and countable at the " "same time")
    if multiple:
        nr_of_elections = 4
        election_meta = {
            "candidate_type": "single",
            "candidate_rules": {
                "seats": nr_of_seats,
                "substitutes": nr_of_substitutes,
                "candidate_gender": True,
            },
            "ballot_rules": {
                "voting": "rank_candidates",
                "votes": nr_of_votes,
            },
            "counting_rules": {
                "method": election_group.meta["counting_rules"]["method"],
                "affirmative_action": election_group.meta["counting_rules"][
                    "affirmative_action"
                ],
            },
        }
    else:
        nr_of_elections = 1
        election_meta = {
            "candidate_type": "single_team",
            "candidate_rules": {
                "seats": 1,
            },
            "ballot_rules": {
                "voting": "rank_candidates",
                "votes": nr_of_votes,
            },
            "counting_rules": {
                "method": election_group.meta["counting_rules"]["method"],
            },
        }
    # In future, running, in past
    if running:
        start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=1
        )
        end = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    elif countable:
        start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=4
        )
        end = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
    else:
        # Default is elections in the future
        start = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=1
        )
        end = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)

    elections = []
    candidate_type = election_group.meta["candidate_type"]
    for i in range(nr_of_elections):
        name_rand = "".join(random.choices(string.ascii_lowercase, k=10))
        election_name = "election-{}".format(name_rand)

        data = {
            "name": {
                "nb": election_name,
                "en": election_name,
            },
            "description": {
                "nb": "Description {}".format(i),
                "en": "Description {}".format(i),
            },
            "group_id": election_group.id,
            "start": start,
            "end": end,
            "active": True,
            "mandate_period_start": (
                datetime.date.today() + datetime.timedelta(days=30)
            ),
            "mandate_period_end": (
                datetime.date.today() + datetime.timedelta(weeks=200)
            ),
            "meta": election_meta,
        }
        election = evalg.database.query.get_or_create(db_session, Election, **data)
        db_session.add(election)
        db_session.flush()

        election_list = ElectionList(
            election_id=str(election.id),
            name={"nb": election_name, "en": election_name},
        )
        db_session.add(election_list)
        election.lists = [election_list]

        candidate_list = election.lists[0]
        for _ in range(candidates_per_pollbook // 2):
            candidate_generator(
                db_session, candidate_type, candidate_list, gender="male"
            )
        for _ in range(candidates_per_pollbook // 2):
            candidate_generator(
                db_session, candidate_type, candidate_list, gender="female"
            )
        if candidates_per_pollbook % 2:
            # Add the correct nr of candidates if
            # candidates_per_pollbook is odd.
            candidate_generator(
                db_session, candidate_type, candidate_list, gender="female"
            )

        if multiple:
            election.pollbooks = [
                pollbook_generator(
                    db_session,
                    election,
                    with_self_added_voters=with_self_added_voters,
                    voters_with_votes=voters_with_votes,
                )
            ]
        else:
            election.pollbooks = [
                pollbook_generator(
                    db_session,
                    election,
                    with_self_added_voters=with_self_added_voters,
                    weight=weight,
                    voters_with_votes=voters_with_votes,
                )
                for weight in [53, 22, 25]
            ]
        db_session.flush()
        elections.append(election)
    return elections


@pytest.fixture
def election_group_generator(db_session, logged_in_user, election_keys):
    def election_group_generator(
        multiple=False,
        owner=False,
        running=False,
        election_type="uio_stv",
        affirmative_action="gender_40",
        candidates_per_pollbook=1,
        nr_of_seats=1,
        nr_of_substitutes=2,
        with_self_added_voters=False,
        countable=False,
        published=False,
        counted=False,
        logged_in_user_in_census=False,
        voters_with_votes=False,
        with_key=True,
    ):
        """Generate different types of elections."""
        if running and countable:
            raise ValueError(
                "Election can't be running and countable at the " "same time"
            )

        if countable and with_self_added_voters:
            raise ValueError(
                "Election can't have self added voters and be "
                "countable at the same time"
            )

        if counted and running:
            raise ValueError(
                "Election can't be counted and running " "at the same time"
            )

        if counted:
            countable = True

        if countable or running:
            published = True
            with_key = True

        if election_type == "mntv":
            nr_of_votes = "nr_of_seats"
        else:
            nr_of_votes = "all"

        name_rand = "".join(random.choices(string.ascii_lowercase, k=10))
        name = "election_group-{}".format(name_rand)

        if multiple:
            election_group_type = "multiple_elections"
            meta = {
                "candidate_type": "single",
                "candidate_rules": {
                    "seats": nr_of_seats,
                    "substitutes": nr_of_substitutes,
                    "candidate_gender": True,
                },
                "ballot_rules": {"voting": "rank_candidates", "votes": nr_of_votes},
                "counting_rules": {
                    "method": election_type,
                    "affirmative_action": [affirmative_action]
                    if affirmative_action
                    else [],
                },
            }
        else:
            election_group_type = "single_election"
            meta = {
                "candidate_type": "single_team",
                "candidate_rules": {"seats": nr_of_seats},
                "ballot_rules": {"voting": "rank_candidates", "votes": nr_of_votes},
                "counting_rules": {"method": election_type},
            }
        data = {
            "name": {
                "nb": name,
                "nn": name,
                "en": name,
            },
            "type": election_group_type,
            "description": {
                "nb": "Description foo",
                "nn": "Description foo",
                "en": "Description foo",
            },
            "meta": meta,
        }

        election_group = evalg.database.query.get_or_create(
            db_session, ElectionGroup, **data
        )
        db_session.add(election_group)

        if with_key:
            election_group.public_key = election_keys["public"]
            db_session.add(election_group)

        db_session.flush()

        if election_type == "party_list":
            election_group.elections = list_election_generator(
                db_session, election_group
            )
        else:
            election_group.elections = new_elections_generator(
                db_session,
                election_group,
                countable=countable,
                running=running,
                nr_of_seats=nr_of_seats,
                nr_of_substitutes=nr_of_substitutes,
                candidates_per_pollbook=candidates_per_pollbook,
                with_self_added_voters=with_self_added_voters,
                voters_with_votes=voters_with_votes,
                multiple=multiple,
                nr_of_votes=nr_of_votes,
            )
        if owner:
            current_user_principal = evalg.proc.authz.get_or_create_principal(
                db_session, principal_type="person", person_id=logged_in_user.person.id
            )
            evalg.proc.authz.add_election_group_role(
                session=db_session,
                election_group=election_group,
                principal=current_user_principal,
                role_name="admin",
            )

        if published:
            election_group.publish()

        if logged_in_user_in_census:
            pollbook = election_group.elections[0].pollbooks[0]
            voter_policy = ElectionVoterPolicy(db_session)
            voter_policy.add_voter(pollbook, logged_in_user.person)

        db_session.flush()

        if counted:
            election_group_counter = evalg.proc.count.ElectionGroupCounter(
                db_session, election_group.id, election_keys["private"]
            )

            count = election_group_counter.log_start_count()
            election_group_counter.deserialize_ballots()
            election_group_counter.process_for_count()

            election_group_counter.generate_results(count)
            election_group_counter.log_finalize_count(count)

        # db_session.commit()
        return election_group

    return election_group_generator


@pytest.fixture
def election_group_grant_generator(
    db_session, person_generator, election_group_generator
):
    """Election group grant for some other person."""

    def election_group_grant(owner=None):
        if owner:
            election_group = election_group_generator(owner=owner)
        else:
            election_group = election_group_generator()
        person = person_generator()
        feide_id = next(i for i in person.identifiers if i.id_type == "feide_id")
        principal = evalg.proc.authz.get_or_create_principal(
            session=db_session,
            principal_type="person_identifier",
            id_type=feide_id.id_type,
            id_value=feide_id.id_value,
        )
        grant = evalg.proc.authz.add_election_group_role(
            session=db_session,
            election_group=election_group,
            principal=principal,
            role_name="admin",
        )
        db_session.flush()
        return grant

    return election_group_grant


@pytest.fixture
def blank_pref_election_ballot_data():
    """Blank pref election ballot data."""

    def blank_pref_election_ballot_data(pollbook):
        return _ballot_data_generator(
            pollbook, vote_type="prefElectVote", blank_vote=True
        )

    return blank_pref_election_ballot_data


@pytest.fixture
def vote_generator(db_session, ballot_data_generator, election_vote_policy_generator):
    """Vote generator."""

    def vote_generator(pollbook, voter, ballot_data=None):
        if not ballot_data:
            candidates = pollbook.election.candidates
            blank_vote = False
            if not candidates or len(candidates) == 0:
                candidates = []
                blank_vote = True

            ballot_data = ballot_data_generator(
                pollbook, blank_vote=blank_vote, candidates=candidates
            )

        election_vote_policy = ElectionVotePolicy(db_session, voter.id)
        return election_vote_policy.add_vote(ballot_data)

    return vote_generator
