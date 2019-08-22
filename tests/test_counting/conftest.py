"""Conftest for counting tests"""

import datetime

import pytest

import evalg.database.query

from evalg.models.candidate import Candidate
from evalg.models.election import Election
from evalg.models.election_list import ElectionList


CANDIDATES_DATA = [
    {
        "name": "Kvinne A",
        "meta": {
            "gender": "female"
        },
    },
    {
        "name": "Kvinne B",
        "meta": {
            "gender": "female"
        },
    },
    {
        "name": "Kvinne C",
        "meta": {
            "gender": "female"
        },
    },
    {
        "name": "Mann D",
        "meta": {
            "gender": "male"
        },
    },
    {
        "name": "Kvinne E",
        "meta": {
            "gender": "female"
        },
    },
    {
        "name": "Kvinne F",
        "meta": {
            "gender": "female"
        },
    },
    {
        "name": "Kvinne G",
        "meta": {
            "gender": "female"
        },
    }
]


ELECTION_LIST_DATA = {
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
def make_election(db_session, election_group_foo):
    """make election fixture"""

    def make_election_w(name, election_group=None):
        """the wrapped make_election function"""
        if not election_group:
            election_group = election_group_foo
        data = {
            'name': {
                'nb': name,
                'en': name,
            },
            'type': 'single_election',
            'description': {
                'nb': 'Description {0}'.format(name),
                'en': 'Description {0}'.format(name),
            },
            'meta': {
                'candidate_rules': {'candidate_gender': True,
                                    'seats': 2,
                                    'substitutes': 2},
                'counting_rules': {'method': 'uio_stv',
                                   'affirmative_action': ['gender_40']},
            },
            # 'active': True,
            'group_id': election_group.id,
            'start': datetime.datetime.now(datetime.timezone.utc),
            'end': datetime.datetime.now(
                datetime.timezone.utc) + datetime.timedelta(days=1)
        }
        election = evalg.database.query.get_or_create(
            db_session, Election, **data)
        db_session.add(election)
        db_session.flush()
        # now the ElectionList
        ELECTION_LIST_DATA['election_id'] = election.id
        election_list = evalg.database.query.get_or_create(
            db_session,
            ElectionList,
            **ELECTION_LIST_DATA)
        db_session.add(election_list)
        db_session.flush()
        # ... and the cadidates
        candidates = [evalg.database.query.get_or_create(
            db_session, Candidate, **x) for x in CANDIDATES_DATA]
        for candidate in candidates:
            election_list.candidates.append(candidate)
        db_session.flush()
        return election

    return make_election_w
