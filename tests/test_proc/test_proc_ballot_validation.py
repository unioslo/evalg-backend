import logging
import pytest
import uuid

from evalg.proc.ballot_verification import (
    BallotVerificationException,
    ListBallotVerifier,
    SuspiciousBallotException,
)

logger = logging.getLogger(__name__)


def test_valid_ballot_blank(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    ballot_data = list_election_ballot_generator(None, blank_vote=True)
    validator = ListBallotVerifier(db_session, voter)
    validator.validate_ballot(ballot_data.copy())


def test_invalid_ballot_blank_with_chosenList(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    ballot_data = list_election_ballot_generator(None, blank_vote=True)

    ballot_data["chosenListId"] = str(election.lists[0].id)

    validator = ListBallotVerifier(db_session, voter)

    with pytest.raises(BallotVerificationException) as excinfo:
        validator.validate_ballot(ballot_data.copy())

    assert f"Blank ballot contains a selected list: {str(election.lists[0].id)}" in str(
        excinfo.value
    )


def test_invalid_ballot_blank_with_personal_votes(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    ballot_data = list_election_ballot_generator(None, blank_vote=True)

    ballot_data["personalVotesSameParty"] = [
        {"candidate": str(x.id), "cumulated": False}
        for x in election.lists[0].candidates[:5]
    ]

    validator = ListBallotVerifier(db_session, voter)

    with pytest.raises(BallotVerificationException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert "Blank ballot contains votes for selected list" in str(excinfo.value)


def test_invalid_ballot_blank_with_personal_votes_other(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    ballot_data = list_election_ballot_generator(None, blank_vote=True)

    ballot_data["personalVotesOtherParty"] = [
        {"candidate": str(x.id), "list": str(election.lists[0].id)}
        for x in election.lists[0].candidates[:5]
    ]

    validator = ListBallotVerifier(db_session, voter)

    with pytest.raises(BallotVerificationException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert "Blank ballot contains personal votes from other lists" in str(excinfo.value)


def test_valid_ballot_clean_vote(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]
    ballot_data = list_election_ballot_generator(
        election_list, candidates_same_list=candidates
    )

    validator = ListBallotVerifier(db_session, voter)
    validator.validate_ballot(ballot_data.copy())


def test_invalid_ballot_no_chosen_list(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]
    ballot_data = list_election_ballot_generator(
        election_list, candidates_same_list=candidates
    )
    ballot_data["chosenListId"] = ""
    validator = ListBallotVerifier(db_session, voter)

    with pytest.raises(BallotVerificationException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert "No election list selected in list" in str(excinfo.value)


def test_invalid_ballot_chosen_list(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]
    ballot_data = list_election_ballot_generator(
        election_list, candidates_same_list=candidates
    )

    other_uuid = str(uuid.uuid4())

    ballot_data["chosenListId"] = other_uuid
    validator = ListBallotVerifier(db_session, voter)

    with pytest.raises(BallotVerificationException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert f"Selected list does not exist. selected_list: {other_uuid}" in str(
        excinfo.value
    )


def test_invalid_ballot_multiple_same_person_vote(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]
    ballot_data = list_election_ballot_generator(
        election_list, candidates_same_list=candidates
    )

    ballot_data["personalVotesSameParty"].append(
        ballot_data["personalVotesSameParty"][4]
    )

    validator = ListBallotVerifier(db_session, voter)
    with pytest.raises(SuspiciousBallotException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert f"Ballot contain duplicate votes in personalVotesSameParty" in str(
        excinfo.value
    )


def test_invalid_ballot_same_person_vote_from_other_list(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]
    ballot_data = list_election_ballot_generator(
        election_list, candidates_same_list=candidates
    )

    other_candidate = str(election.lists[1].candidates[0].id)

    ballot_data["personalVotesSameParty"].append(
        {"candidate": other_candidate, "cumulated": True}
    )

    validator = ListBallotVerifier(db_session, voter)
    with pytest.raises(SuspiciousBallotException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert f"Personal party candidate not in election list, {other_candidate}" in str(
        excinfo.value
    )


def test_valid_edited_ballot(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    """Tests for duplicate candidates in other person votes."""

    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]

    candidates[3]["cumulated"] = True

    candidates_other = [
        {"candidate": str(x.id), "list": str(x.list_id)}
        for x in election.lists[1].candidates[:6]
    ]

    ballot_data = list_election_ballot_generator(
        election_list,
        candidates_same_list=candidates,
        candidates_other=candidates_other,
    )

    validator = ListBallotVerifier(db_session, voter)
    validator.validate_ballot(ballot_data.copy())


def test_invalid_ballot_multiple_other_person_vote(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    """Tests for duplicate candidates in other person votes."""

    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]

    candidates_other = [
        {"candidate": str(x.id), "list": str(x.list_id)}
        for x in election.lists[1].candidates[:6]
    ]

    ballot_data = list_election_ballot_generator(
        election_list,
        candidates_same_list=candidates,
        candidates_other=candidates_other,
    )

    ballot_data["personalVotesOtherParty"].append(
        ballot_data["personalVotesOtherParty"][4]
    )

    validator = ListBallotVerifier(db_session, voter)
    with pytest.raises(SuspiciousBallotException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert f"Ballot contain duplicate votes in personalVotesOtherParty" in str(
        excinfo.value
    )


def test_invalid_ballot_other_vote_from_selected_list(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    """Tests for duplicate candidates in other person votes."""

    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]

    candidates_other = [
        {"candidate": str(x.id), "list": str(x.list_id)}
        for x in election.lists[1].candidates[:6]
    ]

    ballot_data = list_election_ballot_generator(
        election_list,
        candidates_same_list=candidates,
        candidates_other=candidates_other,
    )

    ballot_data["personalVotesOtherParty"].append(
        {"candidate": candidates[3]["candidate"], "list": str(election_list.id)}
    )

    validator = ListBallotVerifier(db_session, voter)
    with pytest.raises(SuspiciousBallotException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert (
        f"Candidate from selected list in other candidates, {candidates[3]['candidate']}"
        in str(excinfo.value)
    )


def test_invalid_ballot_unknown_other_list(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    """Tests for duplicate candidates in other person votes."""

    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]

    candidates_other = [
        {"candidate": str(x.id), "list": str(x.list_id)}
        for x in election.lists[1].candidates[:6]
    ]
    new_uuid = str(uuid.uuid4())
    candidates_other[2]["list"] = new_uuid
    ballot_data = list_election_ballot_generator(
        election_list,
        candidates_same_list=candidates,
        candidates_other=candidates_other,
    )

    validator = ListBallotVerifier(db_session, voter)
    with pytest.raises(SuspiciousBallotException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert (
        "Other candidate list does not exist in election, "
        f"list: {new_uuid} candidate: {candidates_other[2]['candidate']}"
        in str(excinfo.value)
    )


def test_invalid_ballot_unknown_other_candidate(
    db_session,
    list_election_ballot_generator,
    list_election_group,
):
    """Tests for duplicate candidates in other person votes."""

    election = list_election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    election_list = election.lists[0]
    candidates = [
        {"candidate": str(x.id), "cumulated": False} for x in election_list.candidates
    ]

    candidates_other = [
        {"candidate": str(x.id), "list": str(x.list_id)}
        for x in election.lists[1].candidates[:6]
    ]
    new_uuid = str(uuid.uuid4())
    candidates_other[2]["candidate"] = new_uuid
    ballot_data = list_election_ballot_generator(
        election_list,
        candidates_same_list=candidates,
        candidates_other=candidates_other,
    )

    validator = ListBallotVerifier(db_session, voter)
    with pytest.raises(SuspiciousBallotException) as excinfo:
        validator.validate_ballot(ballot_data.copy())
    assert f"Other candidate does not exist in election, candidate:{new_uuid}" in str(
        excinfo.value
    )
