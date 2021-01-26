"""Provides general testing for different counting algorithms"""
import decimal

from evalg.counting.count import Counter


def test_counting_algorithms_uiostv(election_group_generator):
    """
    Tests for the UiO STV algorithm - case1

    - Election with 7 candidates (6 females and one male).
    - 2 regular and 2 substitutes to elect.
    - No votes
    - Gender quotas
    """
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='uio_stv',
                                              candidates_per_pollbook=7,
                                              nr_of_seats=2,
                                              voters_with_votes=True)
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
    males = [str(c.id) for c in candidates if c.meta['gender'] == 'male']
    assert males
    females = [str(c.id) for c in candidates if c.meta['gender'] == 'female']
    assert females

    # now the counting
    counter = Counter(election, [])  # no test_mode. Real randomization at work
    default_path = counter.count().default_path
    result = default_path.get_result()
    protocol = default_path.get_protocol()
    result_dict = result.to_dict()
    election_protocol_dict = protocol.to_dict()
    # test result #
    assert result_dict
    # test if result is JSON serializable #
    assert result.to_json()
    # empty ballot election can only be decided by drawing
    assert result_dict['meta']['drawing']
    # 2 regular and 2 substitutes should have been elected
    assert len(result_dict['regular_candidates']) == 2
    assert len(result_dict['substitute_candidates']) == 2

    # One of the male candidates should have been elected as a regular candidate
    assert [x for x in result_dict['regular_candidates'] if x in males]

    # One of the female candidates should have been elected as a regular candidate
    assert [x for x in result_dict['regular_candidates'] if x in females]

    # test the protocol #
    assert election_protocol_dict
    assert (''.join(result_dict['regular_candidates']) ==
            ''.join(election_protocol_dict['meta']['regular_candidate_ids']))
    assert (
        ''.join(result_dict['substitute_candidates']) ==
        ''.join(election_protocol_dict['meta']['substitute_candidate_ids']))
    # more detailed checks
    elected_events_cnt = 0
    for cround in election_protocol_dict['rounds']:
        for event in cround:
            # no candidate should be elected by surpassing the election number
            assert event['event_type'] != 'CANDIDATE_ELECTED'
            if event['event_type'] == 'CANDIDATE_ELECTED_19_1':
                elected_events_cnt += 1
    # all four candidates (regular + substitutes) must be elected by §19.1
    assert elected_events_cnt == 4
    # test if protocol is JSON serializable #
    assert protocol.to_json()
    # cheap check to make sure that the protocol rendering is complete
    assert protocol.render()
    # more tests / checks should be added in the future


def test_counting_algorithms_uiomv(election_group_generator):
    """
    Tests for the UiO MV algorithm - case1

    - Election with 2 candidates.
    - 1 regular candidate to elect.
    - No votes
    """
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='uio_mv',
                                              candidates_per_pollbook=2,
                                              nr_of_seats=1,
                                              nr_of_substitutes=0,
                                              voters_with_votes=True)
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
    assert len(candidates) == 2  # should be 2 candidates
    # now the counting
    counter = Counter(election, [])  # no test_mode. Real randomization at work
    default_path = counter.count().default_path
    result = default_path.get_result()
    protocol = default_path.get_protocol()
    result_dict = result.to_dict()
    election_protocol_dict = protocol.to_dict()
    # test result #
    assert result_dict
    # test if result is JSON serializable #
    assert result.to_json()
    # empty ballot election can only be decided by drawing
    assert result_dict['meta']['drawing']
    # 1 regular candidate should have been elected
    assert len(result_dict['regular_candidates']) == 1
    # test the protocol #
    assert election_protocol_dict
    assert (''.join(result_dict['regular_candidates']) ==
            ''.join(election_protocol_dict['meta']['regular_candidate_ids']))
    # more detailed checks
    # cheap check to make sure that the protocol rendering is complete
    assert protocol.to_json()
    assert protocol.render()
    # more tests / checks should be added in the future


def test_counting_algorithms_ntnucv(election_group_generator):
    """
    Tests for the NTNU CV algorithm - case1

    - Election with 7 candidates (6 females and one male).
    - 1 regular and 1 substitute to elect.
    - No votes
    - Gender quotas
    """
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='ntnu_cv',
                                              affirmative_action='gender_40',
                                              candidates_per_pollbook=7,
                                              nr_of_seats=1,
                                              nr_of_substitutes=1)
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
    males = [str(c.id) for c in candidates if c.meta['gender'] == 'male']
    assert males
    females = [str(c.id) for c in candidates if c.meta['gender'] == 'female']
    assert females

    # now the counting
    counter = Counter(election, [])  # no test_mode. Real randomization at work
    default_path = counter.count().default_path
    result = default_path.get_result()
    protocol = default_path.get_protocol()
    result_dict = result.to_dict()
    election_protocol_dict = protocol.to_dict()
    # test result #
    assert result_dict
    # test if result is JSON serializable #
    assert result.to_json()
    # empty ballot election can only be decided by drawing
    assert result_dict['meta']['drawing']
    # 1 regular and 1 substitutes should have been elected
    assert len(result_dict['regular_candidates']) == 1
    assert len(result_dict['substitute_candidates']) == 1

    # One male candidate should have been elected
    assert ([x for x in result_dict['regular_candidates'] if x in males] or
            [x for x in result_dict['substitute_candidates'] if x in males])

    # One female candidate should have been elected
    assert ([x for x in result_dict['regular_candidates'] if x in females] or
            [x for x in result_dict['substitute_candidates'] if x in females])

    # test the protocol #
    assert election_protocol_dict
    assert (''.join(result_dict['regular_candidates']) ==
            ''.join(election_protocol_dict['meta']['regular_candidate_ids']))
    assert (
        ''.join(result_dict['substitute_candidates']) ==
        ''.join(election_protocol_dict['meta']['substitute_candidate_ids']))
    # test if protocol is JSON serializable #
    assert protocol.to_json()
    # cheap check to make sure that the protocol rendering is complete
    assert protocol.render()
    # more tests / checks should be added in the future
