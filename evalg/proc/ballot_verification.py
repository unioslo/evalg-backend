import logging

from abc import ABC, abstractmethod

from flask_allows import wants_request

from evalg.models.voter import Voter
from evalg.models.election_list import ElectionList


logger = logging.getLogger(__name__)


class BallotVerificationException(Exception):
    """General exception used for error is ballot validation."""

    pass


class BallotStructureException(BallotVerificationException):
    """
    General exception used for error is ballots structure.

    Missing fields, extra fields, field type errors etc.
    """

    pass


class SuspiciousBallotException(BallotVerificationException):
    """Exception used to for suspicious ballots."""

    pass


class AbstractBallotVerifier(ABC):
    """Abstract ballot verifier"""

    def __init__(self, session, voter: Voter):
        self.session = session
        self.voter = voter
        self.election = voter.pollbook.election

    @abstractmethod
    def validate_ballot(self, ballot_data: dict):
        pass


class ListBallotVerifier(AbstractBallotVerifier):
    def validate_ballot(self, ballot_data: dict):
        try:
            self.validate_fields(ballot_data)
            if ballot_data["isBlankVote"]:
                self.validate_blank_vote(ballot_data)
            else:
                selected_list = self.validate_selected_list(ballot_data)
                self.validate_selected_list_candidates(ballot_data, selected_list)
                self.validate_other_candidates(ballot_data, selected_list)
        except BallotVerificationException as e:
            logger.warning(
                "Ballot verification failed, possible suspect ballot. "
                "voter: %s, election: %s, error: %s",
                self.voter.id,
                self.election.id,
                e,
            )
            return False

        logger.info(
            "Ballot validation OK, voter: %s, election %s",
            self.voter.id,
            self.election.id,
        )
        return True

    def validate_fields(self, ballot_data):
        """Check that the ballot has the required fields."""
        fields = [
            "voteType",
            "chosenListId",
            "isBlankVote",
            "personalVotesOtherParty",
            "personalVotesSameParty",
        ]

        for field in fields:
            if field not in ballot_data:
                raise BallotStructureException(f"Field {field} missing from ballot")

        if len(ballot_data.keys()) != len(fields):
            raise BallotStructureException("Ballot contains unexpected fields")

        if ballot_data["voteType"] != "SPListElecVote":
            raise BallotStructureException("voteType is not correct for the election")

        votes_other_fields = ["candidate", "list"]
        for candidate in ballot_data["personalVotesOtherParty"]:
            for field in votes_other_fields:
                if field not in candidate:
                    raise BallotStructureException(
                        f"Field {field} missing from other candidate"
                    )
            if len(candidate.keys()) != len(votes_other_fields):
                raise BallotStructureException("Ballot contains unexpected fields")

        votes_fields = ["candidate", "cumulated"]
        for candidate in ballot_data["personalVotesSameParty"]:

            for field in votes_fields:
                if field not in candidate:
                    raise BallotStructureException(
                        f"Field {field} missing from votes candidate"
                    )
            if len(candidate.keys()) != len(votes_fields):
                raise BallotStructureException("Ballot contains unexpected fields")

    def validate_blank_vote(self, ballot_data: dict):
        if ballot_data["chosenListId"]:
            raise BallotVerificationException(
                f"Blank ballot contains a selected list: {ballot_data['chosenListId']}"
            )
        if ballot_data["personalVotesOtherParty"]:
            raise BallotVerificationException(
                "Blank ballot contains personal votes from other lists"
            )
        if ballot_data["personalVotesSameParty"]:
            raise BallotVerificationException(
                "Blank ballot contains votes for selected list"
            )

    def validate_selected_list(self, ballot_data: dict) -> ElectionList:
        """
        Validates the selected list, check that is exists and that it belong
        to the current election.
        """
        if not ballot_data["chosenListId"]:
            raise BallotVerificationException("No election list selected in list")
        selected_list: ElectionList = ElectionList.query.get(
            ballot_data["chosenListId"]
        )
        if not selected_list:
            raise BallotVerificationException(
                f"Selected list does not exist. selected_list: {ballot_data['chosenListId']}",
            )
        if selected_list.election.id != self.election.id:
            raise SuspiciousBallotException(
                f"Selected list belongs to another election. selected_list: {ballot_data['chosenListId']}",
            )

        return selected_list

    def validate_selected_list_candidates(
        self, ballot_data: dict, selected_list: ElectionList
    ):
        """
        Validates the selected list and candidates from it.


        - Check that all candidates belong to the current list
        - Check that there are noe duplicate candidates
        """

        ballot_candidate_ids = [
            x["candidate"] for x in ballot_data["personalVotesSameParty"]
        ]
        if len(list(set(ballot_candidate_ids))) != len(ballot_candidate_ids):
            raise SuspiciousBallotException(
                f"Ballot contain duplicate votes in personalVotesSameParty"
            )

        # Check that all candidates are from the selected list
        candidates_ids = [str(x.id) for x in selected_list.candidates]
        for candidate in ballot_data["personalVotesSameParty"]:
            if candidate["candidate"] not in candidates_ids:
                raise SuspiciousBallotException(
                    f"Personal party candidate not in election list, {candidate['candidate']}"
                )

    def validate_other_candidates(self, ballot_data, selected_list: ElectionList):
        """
        Validates the other lists candidates.

        - Check that all candidates exists in election
        - Check for duplicates
        - Check that no candidates from the selected list are present
        - Check that the nr of candidates is less then the max nr allowed
        """

        ballot_candidate_ids = [
            x["candidate"] for x in ballot_data["personalVotesOtherParty"]
        ]

        if len(list(set(ballot_candidate_ids))) != len(ballot_candidate_ids):
            raise SuspiciousBallotException(
                f"Ballot contain duplicate votes in personalVotesOtherParty"
            )

        selected_list_candidates_ids = [str(x.id) for x in selected_list.candidates]
        valid_other_list_candidates = {
            str(x.id): [str(y.id) for y in x.candidates]
            for x in self.election.lists
            if x != selected_list
        }

        for candidate in ballot_data["personalVotesOtherParty"]:
            if candidate["candidate"] in selected_list_candidates_ids:
                raise SuspiciousBallotException(
                    f"Candidate from selected list in other candidates, {candidate['candidate']}"
                )

            if candidate["list"] not in valid_other_list_candidates.keys():
                raise SuspiciousBallotException(
                    "Other candidate list does not exist in election, "
                    f"list: {candidate['list']} candidate: {candidate['candidate']}"
                )

            if (
                candidate["candidate"]
                not in valid_other_list_candidates[candidate["list"]]
            ):
                raise SuspiciousBallotException(
                    f"Other candidate does not exist in election, candidate:{candidate['candidate']}"
                )
