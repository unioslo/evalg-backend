import pytest
from faker import Faker

from evalg.graphql.nodes.candidates import Candidate, ElectionList
from evalg.proc.candidate import (
    add_candidate,
    delete_candidate,
    update_candidate,
)

fake = Faker()


def test_update_priority_no_change(db_session, election_list_in_order) -> None:
    """Move from priority n to n. Expect no change"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}

    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[3].id: 3,
        candidate_priority[4].id: 4,
        candidate_priority[5].id: 5,
    }
    candidate = candidate_priority[2]
    ret_value = update_candidate(
        db_session,
        candidate.name,
        candidate.meta,
        candidate.id,
        election_list_in_order.id,
        priority=2,
        pre_cumulated=False,
    )
    assert ret_value
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_update_priority_move_down(db_session, election_list_in_order) -> None:
    """Move a candidate down in priority"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 4,
        candidate_priority[3].id: 2,
        candidate_priority[4].id: 3,
        candidate_priority[5].id: 5,
    }
    candidate = candidate_priority[2]
    ret_value = update_candidate(
        db_session,
        candidate.name,
        candidate.meta,
        candidate.id,
        election_list_in_order.id,
        priority=4,
        pre_cumulated=False,
    )
    assert ret_value
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_update_priority_move_up(db_session, election_list_in_order) -> None:
    """Move a candidate up in priority"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 3,
        candidate_priority[3].id: 4,
        candidate_priority[4].id: 2,
        candidate_priority[5].id: 5,
    }
    candidate = candidate_priority[4]
    ret_value = update_candidate(
        db_session,
        candidate.name,
        candidate.meta,
        candidate.id,
        election_list_in_order.id,
        priority=2,
        pre_cumulated=False,
    )
    assert ret_value
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_update_priority_at_end(db_session, election_list_in_order):
    """Test reassigning the lowest ranked candidate"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[3].id: 3,
        candidate_priority[4].id: 5,
        candidate_priority[5].id: 4,
    }
    candidate = candidate_priority[5]
    ret_value = update_candidate(
        db_session,
        candidate.name,
        candidate.meta,
        candidate.id,
        election_list_in_order.id,
        priority=4,
        pre_cumulated=False,
    )
    assert ret_value
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_update_priority_large(db_session, election_list_in_order):
    """Test reassigning the lowest ranked candidate"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[3].id: 3,
        candidate_priority[4].id: 4,
        candidate_priority[5].id: 5,
    }
    candidate = candidate_priority[5]
    ret_value = update_candidate(
        db_session,
        candidate.name,
        candidate.meta,
        candidate.id,
        election_list_in_order.id,
        priority=40,
        pre_cumulated=False,
    )
    assert ret_value
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_update_priority_at_start(db_session, election_list_in_order) -> None:
    """Test reassign of the highest ranked candidate."""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    expected_priority = {
        candidate_priority[1].id: 4,
        candidate_priority[2].id: 1,
        candidate_priority[3].id: 2,
        candidate_priority[4].id: 3,
        candidate_priority[5].id: 5,
    }
    candidate = candidate_priority[1]
    ret_value = update_candidate(
        db_session,
        candidate.name,
        candidate.meta,
        candidate.id,
        election_list_in_order.id,
        priority=4,
        pre_cumulated=False,
    )
    assert ret_value
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_add_new_priority_at_end(
    db_session,
    election_list_in_order,
) -> None:
    """Add a new candidate at the end. There should be no change to the priority list."""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    add_candidate(
        session=db_session,
        name=fake.name(),
        meta={"field_of_study": fake.job()},
        election_list_id=str(election_list_in_order.id),
        information_url="",
        priority=len(election_list_in_order.candidates) + 1,
        pre_cumulated=False,
    )
    new_candidates = set(election_list_in_order.candidates) - set(
        candidate_priority.values()
    )
    assert len(new_candidates) == 1
    new_candidate = new_candidates.pop()
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[3].id: 3,
        candidate_priority[4].id: 4,
        candidate_priority[5].id: 5,
        new_candidate.id: 6,
    }
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


@pytest.mark.test
def test_add_new_priority_at_start(
    db_session,
    candidate_generator,
    election_list_in_order,
) -> None:
    """Add a new candidate at the start. All other candidates should be shifted one space down"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    ret_value = add_candidate(
        session=db_session,
        name=fake.name(),
        meta={"field_of_study": fake.job()},
        election_list_id=str(election_list_in_order.id),
        information_url="",
        priority=1,
        pre_cumulated=False,
    )
    assert ret_value
    new_candidates = set(election_list_in_order.candidates) - set(
        candidate_priority.values()
    )
    assert len(new_candidates) == 1
    new_candidate = new_candidates.pop()
    expected_priority = {
        candidate_priority[1].id: 2,
        candidate_priority[2].id: 3,
        candidate_priority[3].id: 4,
        candidate_priority[4].id: 5,
        candidate_priority[5].id: 6,
        new_candidate.id: 1,
    }
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_add_new_priority_in_middle(
    db_session,
    candidate_generator,
    election_list_in_order,
) -> None:
    """Add a new candidate in the middle."""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    add_candidate(
        session=db_session,
        name=fake.name(),
        meta={"field_of_study": fake.job()},
        election_list_id=str(election_list_in_order.id),
        information_url="",
        priority=3,
        pre_cumulated=False,
    )
    new_candidates = set(election_list_in_order.candidates) - set(
        candidate_priority.values()
    )
    assert len(new_candidates) == 1
    new_candidate = new_candidates.pop()
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[3].id: 4,
        candidate_priority[4].id: 5,
        candidate_priority[5].id: 6,
        new_candidate.id: 3,
    }
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_delete_at_start(
    db_session,
    election_list_in_order,
) -> None:
    """Delete a candidate at the start"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    delete_candidate(session=db_session, candidate_id=candidate_priority[1].id)
    expected_priority = {
        candidate_priority[2].id: 1,
        candidate_priority[3].id: 2,
        candidate_priority[4].id: 3,
        candidate_priority[5].id: 4,
    }
    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_delete_at_end(
    db_session,
    election_list_in_order,
) -> None:
    """Delete a candidate at the end"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    delete_candidate(session=db_session, candidate_id=candidate_priority[5].id)
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[3].id: 3,
        candidate_priority[4].id: 4,
    }

    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority


def test_delete_in_middle(
    db_session,
    election_list_in_order,
) -> None:
    """Delete a candidate in the middle"""
    candidate_priority = {c.priority: c for c in election_list_in_order.candidates}
    delete_candidate(session=db_session, candidate_id=candidate_priority[3].id)
    expected_priority = {
        candidate_priority[1].id: 1,
        candidate_priority[2].id: 2,
        candidate_priority[4].id: 3,
        candidate_priority[5].id: 4,
    }

    candidate_priority_after = {
        c.id: c.priority for c in election_list_in_order.candidates
    }
    assert candidate_priority_after == expected_priority
