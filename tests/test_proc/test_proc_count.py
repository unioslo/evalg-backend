
from evalg.models.pollbook import PollBook
from evalg.models.election_result import ElectionResult
from evalg.proc.count import ElectionGroupCounter


def test_election_group_counter(
        election_group_bar,
        pref_candidates_bar,
        pollbook_bar,
        pollbook_voter_bar,
        envelope_bar,
        vote_bar,
        election_keys_foo,
        db_session
):
    election_group_counter = ElectionGroupCounter(
        db_session,
        election_group_bar.id,
        election_keys_foo['private']
    )

    count = election_group_counter.log_start_count()
    assert count.status == 'ongoing'
    election_group_counter.deserialize_ballots()
    pollbook = election_group_counter.group.elections[0].pollbooks[0]
    assert pollbook.ballots[0].ballot_data
    election_group_counter.process_for_count()
    assert pollbook.weight_per_vote == 1
    assert pollbook.weight_per_pollbook == 1
    election_group_counter.generate_results(count)

    election_result = db_session.query(
        ElectionResult
    ).filter(
        ElectionResult.election_group_count_id == count.id
    ).first()

    assert election_result.result.get('elected_regular_candidates')[0]
    election_group_counter.log_finalize_count(count)
    assert count.status == 'finished'
