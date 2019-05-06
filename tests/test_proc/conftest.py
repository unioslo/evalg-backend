import pytest

from evalg.proc.vote import ElectionVotePolicy


@pytest.fixture
def election_vote_policy_foo(db_session):
    return ElectionVotePolicy(db_session)

