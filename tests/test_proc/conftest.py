import datetime
from pyparsing import dbl_slash_comment
import pytest

from typing import Callable

from sqlalchemy.orm.scoping import scoped_session
from faker import Faker

import evalg
from evalg.models.pollbook import Pollbook, Voter
from evalg.models.candidate import Candidate
from evalg.models.election import Election, ElectionGroup
from evalg.models.election_list import ElectionList

fake = Faker()


@pytest.fixture
def candidate_generator(
    db_session: scoped_session,
) -> Callable[[ElectionList, int], Candidate]:
    def candidate_generator(election_list, priority):
        candidate = Candidate(
            name=fake.name(),
            meta={"field_of_study": fake.job()},
            list=election_list,
            priority=priority,
            pre_cumulated=False,
        )
        return candidate

    return candidate_generator


@pytest.fixture
def election_list_in_order(
    db_session,
    candidate_generator,
    election_group_generator,
) -> ElectionList:
    election_group = election_group_generator(election_type="party_list")

    election_list = ElectionList(
        election=election_group.elections[0],
        name={"nb": "Test 123", "en": "Test 123"},
    )

    db_session.add(election_list)
    db_session.flush()

    for x in range(1, 6):
        db_session.add(candidate_generator(election_list, x))

    db_session.commit()

    return election_list


@pytest.fixture
def list_election_group(db_session, election_keys) -> ElectionGroup:

    meta = {
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
    data = {
        "name": {
            "nb": fake.name(),
            "nn": fake.name(),
            "en": fake.name(),
        },
        "type": "single_election",
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
    election_group.public_key = election_keys["public"]
    election_group.publish()

    db_session.add(election_group)

    start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    end = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)

    data = {
        "name": {
            "nb": fake.name(),
            "en": fake.name(),
        },
        "description": {
            "nb": "Description foo",
            "en": "Description foo",
        },
        "group_id": election_group.id,
        "start": start,
        "end": end,
        "active": True,
        "mandate_period_start": (datetime.date.today() + datetime.timedelta(days=30)),
        "mandate_period_end": (datetime.date.today() + datetime.timedelta(weeks=200)),
        "meta": {
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
        },
    }
    election = evalg.database.query.get_or_create(db_session, Election, **data)
    db_session.add(election)
    election_group.elections = [election]
    db_session.flush()

    election_lists = []
    for x in range(5):
        election_list = ElectionList(
            election_id=str(election.id),
            name={"nb": fake.company(), "en": fake.company()},
        )

        db_session.add(election_list)
        db_session.flush()
        election_lists.append(election_list)

        candidates = []
        for i in range(20):

            candidate_data = {
                "list_id": election_list.id,
                "name": fake.name(),
                "meta": {"field_of_study": fake.job()},
                "priority": i,
                "pre_cumulated": True if i < 5 else False,
            }
            candidate = evalg.database.query.get_or_create(
                db_session, Candidate, **candidate_data
            )
            candidates.append(candidate)
            db_session.add(candidate)

        election_list.candidates = candidates
        db_session.flush()

    election.lists = election_lists

    pollbook_data = {
        "name": {
            "nb": fake.name(),
            "en": fake.name(),
        },
        "election_id": election.id,
        "weight": 100,
        "priority": 0,
    }

    pollbook = evalg.database.query.get_or_create(db_session, Pollbook, **pollbook_data)
    db_session.add(pollbook)

    voter_data = {
        "id_type": "feide_id",
        "id_value": "test@example.org",
        "pollbook_id": pollbook.id,
        "self_added": False,
        "reviewed": False,
        "verified": True,
    }

    pollbook.voters = [
        evalg.database.query.get_or_create(db_session, Voter, **voter_data)
    ]

    election.pollbooks = [pollbook]
    db_session.flush()

    return election_group


@pytest.fixture
def list_election_ballot_generator() -> Callable[..., dict]:
    def list_election_ballot_generator(
        selected_list: ElectionList,
        candidates_same_list=[],
        candidates_other=[],
        blank_vote=False,
    ):

        if blank_vote:
            return {
                "voteType": "SPListElecVote",
                "chosenListId": "",
                "isBlankVote": True,
                "personalVotesOtherParty": [],
                "personalVotesSameParty": [],
            }

        ballot_data = {
            "voteType": "SPListElecVote",
            "chosenListId": str(selected_list.id),
            "isBlankVote": False,
            "personalVotesOtherParty": candidates_other,
            "personalVotesSameParty": candidates_same_list,
        }

        return ballot_data

    return list_election_ballot_generator
