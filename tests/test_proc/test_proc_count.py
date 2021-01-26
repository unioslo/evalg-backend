
from evalg.models.election_result import ElectionResult
from evalg.proc.count import ElectionGroupCounter


def test_election_group_counter(db_session,
                                election_group_generator,
                                election_keys):
    election_group = election_group_generator(owner=True,
                                              multiple=True,
                                              countable=True,
                                              voters_with_votes=True)
    voters = election_group.elections[0].pollbooks[0].voters
    voters_with_votes = [x for x in voters if x.has_voted]
    election_group_counter = ElectionGroupCounter(db_session,
                                                  election_group.id,
                                                  election_keys['private'],
                                                  test_mode=True)
    count = election_group_counter.log_start_count()
    assert count.status == 'ongoing'
    election_group_counter.deserialize_ballots()
    pollbook = election_group_counter.group.elections[0].pollbooks[0]
    assert pollbook.ballots[0].ballot_data
    election_group_counter.process_for_count()
    assert float(pollbook.weight_per_vote) == 1 / len(voters_with_votes)
    assert pollbook.weight_per_pollbook == 1
    election_group_counter.generate_results(count, 'Test Runner')

    election_result = db_session.query(
        ElectionResult
    ).filter(
        ElectionResult.election_group_count_id == count.id
    ).first()

    assert election_result.result.get('regular_candidates')[0]
    election_group_counter.log_finalize_count(count)
    assert count.status == 'finished'
