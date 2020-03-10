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

    def make_election_w(name,
                        election_group=None,
                        seats=2,
                        substitutes=2,
                        election_type='uio_stv'):
        """the wrapped make_uiostv_election function"""
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
            'meta': {
                'candidate_rules': {'candidate_gender': True,
                                    'seats': seats,
                                    'substitutes': substitutes},
                'counting_rules': {'method': election_type,
                                   'affirmative_action': []}
            },
            # 'active': True,
            'group_id': election_group.id,
            'start': datetime.datetime.now(datetime.timezone.utc),
            'end': datetime.datetime.now(
                datetime.timezone.utc) + datetime.timedelta(days=1)
        }
        if election_type in ('uio_stv', 'ntnu_cv'):
            data['meta']['counting_rules']['affirmative_action'] = [
                'gender_40']
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
        if election_type == 'uio_mv':
            # 2 candidates only for uio_mv
            candidates_data = CANDIDATES_DATA[:2]
        else:
            candidates_data = CANDIDATES_DATA
        candidates = [evalg.database.query.get_or_create(
            db_session, Candidate, **x) for x in candidates_data]
        for candidate in candidates:
            election_list.candidates.append(candidate)
        db_session.flush()
        return election

    return make_election_w


@pytest.fixture
def make_full_election(
        make_election_group,
        make_election,
        make_pollbook,
        person_generator,
        make_pollbook_voter,
        make_pollbook_vote):
    """make_full_election fixture"""
    def make_full_election_w(name,
                             nr_of_elections=2,
                             pollboks_per_election=1,
                             seats=2,
                             substitutes=2,
                             election_type='uio_stv',
                             voters_per_pollbook=1):
        """creates an entire election-group with elections"""
        election_group = make_election_group('Test election group')

        elections = [make_election(
            '{0} election {1}'.format(name, x),
            election_group=election_group,
            seats=seats,
            substitutes=substitutes,
            election_type=election_type) for x in
                     range(1, nr_of_elections+1)]

        pollbooks = {}
        pollbook_voters = {}
        persons_all = []
        voters_all = []

        for election in elections:

            pollbooks[str(election.id)] = ([make_pollbook(
                '{0} pollbook {1}'.format(election.name, x),
                election=election) for x in range(0, pollboks_per_election)])

            for pollbook in pollbooks[str(election.id)]:
                p = [person_generator('{0} test person {1}'.format(
                    pollbook.name, x), '{0}-{1}@example.org'.format(
                        name, x)) for x in range(0, voters_per_pollbook)]
                persons_all.extend(p)
                v = [make_pollbook_voter(x, pollbook) for x in p]

                voters_all.extend(v)
                pollbook_voters[str(pollbook.id)] = v

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

    return make_full_election_w
