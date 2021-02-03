
import decimal
import logging
import math
import pytest

from evalg.counting.count import Counter
from evalg.proc.vote import ElectionVotePolicy
from evalg.proc.count import ElectionGroupCounter

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'seats, substitutes',
    [(1, 0),
     (2, 0),
     (3, 0),
     (1, 1),
     (1, 2),
     (1, 3),
     (3, 3),
     ]
)
def test_no_votes(seats, substitutes, election_group_generator):
    """
    Tests for the MV algorithm - case1

    - Election with 2 candidates.
    - 1 regular candidate to elect.
    - No votes
    """
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='mntv',
                                              candidates_per_pollbook=7,
                                              nr_of_seats=seats,
                                              nr_of_substitutes=substitutes)
    election = election_group.elections[0]
    # duplicate the process_for_count functionality
    for pollbook in election.pollbooks:
        pollbook.ballots_count = 0
        pollbook.counting_ballots_count = 0
        pollbook.empty_ballots_count = 0
        pollbook.weight_per_vote = decimal.Decimal(0)
        pollbook.weight_per_pollbook = decimal.Decimal(1)
    election.ballots = []
    election.total_amount_ballots = 0
    election.total_amount_empty_ballots = 0
    election.total_amount_counting_ballots = 0
    # sanity checks before counting ...
    candidates = election.candidates
    assert len(candidates) == 7  # should be 7 candidates
    # now the counting
    counter = Counter(election, [])  # no test_mode. Real randomization at work
    default_path = counter.count().default_path
    result = default_path.get_result()
    protocol = default_path.get_protocol()
    result_dict = result.to_dict()
    election_protocol_dict = protocol.to_dict()

    # test result
    assert result_dict

    # test if result is JSON serializable
    assert result.to_json()

    # empty ballot election can only be decided by drawing
    assert result_dict['meta']['drawing']

    # Check that we got the correct nr of elected candidates
    assert len(result_dict['regular_candidates']) == seats

    # Check that we got the correct nr of elected
    assert len(result_dict['substitute_candidates']) == substitutes

    # test the protocol #
    assert election_protocol_dict
    assert (''.join(result_dict['regular_candidates']) ==
            ''.join(election_protocol_dict['meta']['regular_candidate_ids']))

    # more detailed checks
    # cheap check to make sure that the protocol rendering is complete
    assert protocol.to_json()
    assert protocol.render()


@pytest.mark.parametrize(
    'seats, substitutes, vote_data, elected_regular, elected_subs',
    [
        (
            1,
            0,
            [
                [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
                [0, 0, 0, 1, 1, 1, 1, 1, 2, 2],
                [0, 0, 0, 0, 0, 0, 1, -1, -1, -1],
                [0, 2, 2, 2, 2, 0, 1, -1, -1, -1],
            ],
            [[0], [1], [0], [2]],
            [[], [], [], []],
        ),
        (
            2,
            0,
            [
                [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
                [0, 0, 0, 1, 1, 1, 1, 1, 2, 2],
                [0, 0, 0, 0, 0, 0, 1, -1, -1, -1],
                [0, 2, 2, 2, 2, 0, 1, -1, -1, -1],
            ],
            [[0, 1], [1, 0], [0, 1], [2, 0]],
            [[], [], [], []],
        ),
        (
            0,
            1,
            [
                [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
                [0, 0, 0, 1, 1, 1, 1, 1, 2, 2],
                [0, 0, 0, 0, 0, 0, 1, -1, -1, -1],
                [0, 2, 2, 2, 2, 0, 1, -1, -1, -1],
            ],
            [[], [], [], []],
            [[0], [1], [0], [2]],
        ),
        (
            1,
            1,
            [
                [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
                [0, 0, 0, 1, 1, 1, 1, 1, 2, 2],
                [0, 0, 0, 0, 0, 0, 1, -1, -1, -1],
                [0, 2, 2, 2, 2, 0, 1, -1, -1, -1],
            ],
            [[0], [1], [0], [2]],
            [[1], [0], [1], [0]],
        ),
        (
                1,
                2,
                [
                    [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
                    [0, 0, 0, 1, 1, 1, 1, 1, 2, 2],
                    [0, 0, 0, 0, 0, 0, 2, 2, 1, -1],
                    [0, 2, 2, 2, 2, 0, 1, -1, -1, -1],
                ],
                [[0], [1], [0], [2]],
                [[1, 2], [0, 2], [2, 1], [0, 1]],
        ),
    ]
)
def test_election_clear_winner(
        seats,
        substitutes,
        vote_data,
        elected_regular,
        elected_subs,
        db_session,
        election_group_generator,
        ballot_data_generator,
        election_keys,
        vote_generator):
    """Team election with a clear winner."""

    # Candidate index to vote for. -1 == no vote
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='mntv',
                                              affirmative_action=None,
                                              candidates_per_pollbook=6,
                                              nr_of_seats=seats,
                                              nr_of_substitutes=substitutes)
    elected_regular_ids = []
    elected_subs_ids = []
    for i in range(len(elected_regular)):
        candidates = election_group.elections[i].candidates
        elected_regular_ids.append(
            [candidates[elected_regular[i][j]].id
             for j in range(len(elected_regular[i]))])

    for i in range(len(elected_subs)):
        candidates = election_group.elections[i].candidates
        elected_subs_ids.append(
            [candidates[elected_subs[i][j]].id
             for j in range(len(elected_subs[i]))])

    for i, election in enumerate(election_group.elections):
        pollbook = election.pollbooks[0]
        for j, voter in enumerate(pollbook.voters):
            if vote_data[i][j] == -1:
                continue
            candidate_index = vote_data[i][j]
            election_vote_policy = ElectionVotePolicy(db_session, voter.id)
            election_vote_policy.add_vote(ballot_data_generator(
                pollbook,
                vote_type='majorityVote',
                candidates=[election.candidates[candidate_index]]))

    election_group_counter = ElectionGroupCounter(
        db_session,
        election_group.id,
        election_keys['private']
    )
    db_session.commit()

    count = election_group_counter.log_start_count()
    election_group_counter.deserialize_ballots()
    election_group_counter.process_for_count()
    election_group_counter.generate_results(count)
    election_group_counter.log_finalize_count(count)

    for i, r in enumerate(count.election_results):
        result = r.result
        nr_of_votes = len([1 for x in vote_data[i] if x >= 0])

        assert result['meta']['ballots_count'] == nr_of_votes
        assert result['meta']['empty_ballots_count'] == 0

        # Check that we got
        assert len(result['regular_candidates']) == seats
        for j, res_candidate in enumerate(result['regular_candidates']):
            assert res_candidate == str(elected_regular_ids[i][j])

        assert len(result['substitute_candidates']) == substitutes
        for j, res_sub_candidate in enumerate(result['substitute_candidates']):
            assert res_sub_candidate == str(elected_subs_ids[i][j])


def test_team_election_clear_winner(
        db_session,
        election_group_generator,
        ballot_data_generator,
        election_keys,
        vote_generator):
    """Team election with a clear winner."""

    # Candidate index to vote for. -1 == no vote
    vote_data = [
        [0, 0, 0, 0, 0, 1, 1, 1, 2, 2],
        [0, 0, 0, 0, 0, 0, 1, 1, 2, 2],
        [0, 0, 0, 0, 0, 0, 1, -1, -1, -1],
    ]
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=False,
                                              election_type='mntv',
                                              candidates_per_pollbook=3,
                                              nr_of_seats=1,
                                              nr_of_substitutes=0)

    # Only one election
    election = election_group.elections[0]
    winner_id = election.candidates[0].id

    for i, pollbook in enumerate(election.pollbooks):
        for j, voter in enumerate(pollbook.voters):
            if vote_data[i][j] == -1:
                continue
            candidate_index = vote_data[i][j]
            election_vote_policy = ElectionVotePolicy(db_session, voter.id)
            election_vote_policy.add_vote(ballot_data_generator(
                pollbook,
                vote_type='majorityVote',
                candidates=[election.candidates[candidate_index]]))

    election_group_counter = ElectionGroupCounter(
        db_session,
        election_group.id,
        election_keys['private']
    )
    db_session.commit()

    count = election_group_counter.log_start_count()
    election_group_counter.deserialize_ballots()
    election_group_counter.process_for_count()
    election_group_counter.generate_results(count)
    election_group_counter.log_finalize_count(count)
    result = count.election_results[0].result

    nr_of_votes = len([1 for x in vote_data for y in x if y >= 0])

    assert result['meta']['ballots_count'] == nr_of_votes
    assert result['meta']['empty_ballots_count'] == 0
    assert not result['meta']['drawing']

    # Check that we got
    assert len(result['regular_candidates']) == election.num_choosable == 1
    assert result['regular_candidates'][0] == str(winner_id)

    assert len(result['substitute_candidates']) == 0


def test_team_election_weighted_winner(
        db_session,
        election_group_generator,
        ballot_data_generator,
        election_keys,
        vote_generator):
    """
    Test weighting.

    Pollbook 1 has 53% of the vote weight.
    One vote in pollbook 1 is enough.
    """

    # Candidate index to vote for. -1 == no vote
    vote_data = [
        [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
        [1, 1, 1, 1, 1, 1, 1, 1, 2, 2],
        [1, 1, 1, 1, 1, 1, 1, -1, -1, -1],
    ]

    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=False,
                                              election_type='mntv',
                                              candidates_per_pollbook=6,
                                              nr_of_seats=2,
                                              nr_of_substitutes=2)

    # Only one election
    election = election_group.elections[0]
    winner_id = election.candidates[0].id

    for i, pollbook in enumerate(election.pollbooks):
        for j, voter in enumerate(pollbook.voters):
            if vote_data[i][j] == -1:
                continue
            candidate_index = vote_data[i][j]
            election_vote_policy = ElectionVotePolicy(db_session, voter.id)
            election_vote_policy.add_vote(ballot_data_generator(
                pollbook,
                vote_type='majorityVote',
                candidates=[election.candidates[candidate_index]]))

    election_group_counter = ElectionGroupCounter(
        db_session,
        election_group.id,
        election_keys['private']
    )
    db_session.commit()

    count = election_group_counter.log_start_count()
    election_group_counter.deserialize_ballots()
    election_group_counter.process_for_count()
    election_group_counter.generate_results(count)
    election_group_counter.log_finalize_count(count)
    result = count.election_results[0].result

    nr_of_votes = len([1 for x in vote_data for y in x if y >= 0])

    assert result['meta']['ballots_count'] == nr_of_votes
    assert result['meta']['empty_ballots_count'] == 0

    # Check that we got
    assert len(result['regular_candidates']) == election.num_choosable == 1
    assert result['regular_candidates'][0] == str(winner_id)

    assert len(result['substitute_candidates']) == 0


@pytest.mark.parametrize(
    'seats, substitutes, elected_regular, elected_subs',
    [
        (1, 1, [[0], [1], [1], [5]], [[1], [2], [], [4]]),
        (2, 2, [[0, 5], [1], [1], [5, 2]], [[1], [2], [], [4, 1]]),
        (3, 2, [[0, 1, 5], [1, 2], [1], [5, 4, 2]], [[2], [], [], []]),
        (6, 0, [[0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5]],
         [[], [], [], []]),
        (0, 2, [[], [], [], []], [[0, 5], [1], [1], [5, 2]]),
    ])
def test_quotas(seats,
                substitutes,
                elected_regular,
                elected_subs,
                db_session,
                election_group_generator,
                ballot_data_generator,
                election_keys,
                vote_generator):
    """
    Test weighting.

    Pollbook 1 has 53% of the vote weight.
    One vote in pollbook 1 is enough.
    """

    # Candidate index to vote for. -1 == no vote
    # The last half of the generated candidates
    # in the fixture election are female.
    vote_data = [
        [0, 0, 0, 0, 1, 1, 1, 5, 5, 2],
        [1, 1, 1, 1, 1, 1, 1, 1, 2, 2],
        [1, 1, 1, 1, 1, 1, 1, -1, -1, -1],
        [5, 5, 5, 5, 4, 4, 4, 1, 2, 2],

    ]
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='mntv',
                                              candidates_per_pollbook=6,
                                              nr_of_seats=seats,
                                              nr_of_substitutes=substitutes)

    expected_winners_ids = []
    expected_substitutes_ids = []

    for i in range(len(elected_regular)):
        candidates = election_group.elections[i].candidates
        expected_winners_ids.append(
            [str(candidates[elected_regular[i][j]].id)
             for j in range(len(elected_regular[i]))])

    for i in range(len(elected_subs)):
        candidates = election_group.elections[i].candidates
        expected_substitutes_ids.append(
            [str(candidates[elected_subs[i][j]].id)
             for j in range(len(elected_subs[i]))])

    male_candidates = []
    female_candidates = []

    for election in election_group.elections:
        candidates = election.candidates
        male_candidates.append(
            [str(c.id) for c in candidates if c.meta['gender'] == 'male'])
        female_candidates.append(
            [str(c.id) for c in candidates if c.meta['gender'] == 'female'])

    for i, election in enumerate(election_group.elections):
        pollbook = election.pollbooks[0]
        for j, voter in enumerate(pollbook.voters):
            if vote_data[i][j] == -1:
                continue
            candidate_index = vote_data[i][j]
            election_vote_policy = ElectionVotePolicy(db_session, voter.id)
            election_vote_policy.add_vote(ballot_data_generator(
                pollbook,
                vote_type='majorityVote',
                candidates=[election.candidates[candidate_index]]))

    election_group_counter = ElectionGroupCounter(
        db_session,
        election_group.id,
        election_keys['private']
    )
    db_session.commit()

    count = election_group_counter.log_start_count()
    election_group_counter.deserialize_ballots()
    election_group_counter.process_for_count()
    election_group_counter.generate_results(count)
    election_group_counter.log_finalize_count(count)

    for i, r in enumerate(count.election_results):
        result = r.result
        nr_of_votes = len([1 for x in vote_data[i] if x >= 0])

        assert result['meta']['ballots_count'] == nr_of_votes
        assert result['meta']['empty_ballots_count'] == 0
        assert result['meta']['drawing']

        # Check that we got the expected winners
        assert len(result['regular_candidates']) == seats
        for expected_winner_id in expected_winners_ids[i]:
            assert expected_winner_id in result['regular_candidates']

        assert len(result['substitute_candidates']) == substitutes
        for expected_substitutes_id in expected_substitutes_ids[i]:
            assert expected_substitutes_id in result['substitute_candidates']

        # Check that the quotas are filled.
        if seats <= 1:
            min_quota_size = 0
        elif seats <= 3:
            min_quota_size = 1
        else:
            min_quota_size = math.ceil(0.4 * seats)
        max_quota_size = seats - min_quota_size
        regular_female = len([x for x in result['regular_candidates']
                              if x in female_candidates[i]])
        regular_male = len([x for x in result['regular_candidates']
                            if x in male_candidates[i]])
        assert min_quota_size <= regular_female <= max_quota_size
        assert min_quota_size <= regular_male <= max_quota_size

        if substitutes <= 1:
            min_sub_quota_size = 0
        elif substitutes <= 3:
            min_sub_quota_size = 1
        else:
            min_sub_quota_size = math.ceil(0.4 * seats)
        max_sub_quota_size = substitutes - min_sub_quota_size
        subs_female = len([x for x in result['substitute_candidates']
                           if x in female_candidates[i]])
        subs_male = len([x for x in result['substitute_candidates']
                         if x in male_candidates[i]])
        assert min_sub_quota_size <= subs_female <= max_sub_quota_size
        assert min_sub_quota_size <= subs_male <= max_sub_quota_size
