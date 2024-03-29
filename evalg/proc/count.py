"""Module for pre processing data and initiating count"""
import logging
import datetime
import decimal

import nacl.exceptions

from flask import current_app

from sqlalchemy.sql import and_

from sentry_sdk import capture_exception

import evalg.database.query
from evalg.models.ballot import Envelope
from evalg.models.votes import Vote
from evalg.models.election_result import ElectionResult
from evalg.models.election_group_count import ElectionGroupCount
from evalg.models.voter import Voter
from evalg.proc.pollbook import get_verified_voters_count
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer
from evalg.counting.algorithms import party_list, uitstv, positional_voting
from evalg.counting.count import Counter

logger = logging.getLogger(__name__)


class ListBallot:
    def __init__(self, ballot_data, id2pollbook, id2list, id2candidate):
        self.ballot_data = ballot_data
        self.pollbook = id2pollbook[ballot_data["pollbookId"]]
        if ballot_data["chosenListId"]:
            self.chosen_list = id2list[ballot_data["chosenListId"]]
        else:
            self.chosen_list = None

        self.personal_votes_same = [
            {
                "candidate": id2candidate[vote["candidate"]],
                "cumulated": vote["cumulated"],
            }
            for vote in ballot_data["personalVotesSameParty"]
        ]

        self.personal_votes_other = [
            {
                "candidate": id2candidate[vote["candidate"]],
                "list": id2list[vote["list"]],
            }
            for vote in ballot_data["personalVotesOtherParty"]
        ]

        # TODO dette er en hack for å få get_counting_ballots til åfunke
        self.candidates = [1] if self.chosen_list else []

    @property
    def raw_string(self):
        return " ".join(
            [str(self.pollbook.id)]
            + [str(self.chosen_list.id)]
            + [str(candidate["id"]) for candidate in self.personal_votes_same]
            + ["other list:"]
            + [str(candidate["id"]) for candidate in self.personal_votes_other]
        )


class Ballot:
    def __init__(self, ballot_data, id2pollbook, id2candidate):
        self.ballot_data = ballot_data
        self.pollbook = id2pollbook[ballot_data["pollbookId"]]
        self.candidates = [id2candidate[id] for id in ballot_data["rankedCandidateIds"]]

    @property
    def raw_string(self):
        return " ".join(
            [str(self.pollbook.id)]
            + [str(candidate.id) for candidate in self.candidates]
        )


def get_counting_ballots(ballots):
    return list(filter(lambda ballot: ballot.candidates != [], ballots))


def get_empty_ballots(ballots):
    return list(filter(lambda ballot: ballot.candidates == [], ballots))


def get_weight_per_vote(pollbook):
    if pollbook.counting_ballots_count == 0:
        return decimal.Decimal(0)
    return decimal.Decimal(pollbook.weight) / decimal.Decimal(
        pollbook.counting_ballots_count
    )


def set_pollbook_stats(pollbook):
    pollbook.ballots_count = len(pollbook.ballots)
    pollbook.counting_ballots_count = len(get_counting_ballots(pollbook.ballots))
    pollbook.empty_ballots_count = len(get_empty_ballots(pollbook.ballots))
    pollbook.weight_per_vote = get_weight_per_vote(pollbook)


def set_weight_per_pollbook(pollbook, min_wpv):
    pollbook.weight_per_pollbook = pollbook.weight_per_vote / min_wpv


def set_weight_per_pollbooks(pollbooks):
    min_wpv = min(
        [
            pollbook.weight_per_vote
            for pollbook in pollbooks
            if pollbook.weight_per_vote
        ],
        default=decimal.Decimal(1),
    )
    for pollbook in pollbooks:
        set_weight_per_pollbook(pollbook, min_wpv)
        pollbook.scale_factor = decimal.Decimal(1) / min_wpv


class ElectionGroupCounter:
    """The election-group counter class"""

    def __init__(self, session, group_id, election_key, test_mode=False):
        """
        :param session: The DB session object
        :type session: sqlalchemy.orm.session.Session

        :param group_id: The UUID of the election-group
        :type group_id: evalg.database.types.UuidType

        :param election_key: The election private-key to be used for decrypting
        :type election_key: str

        :param test_mode: In case of drawing, generate the same (non-random)
                          "random result(s)"
        :type test_mode: bool
        """
        self.app_config = current_app.config
        self.session = session
        self.group_id = group_id
        self.test_mode = test_mode
        self.group = session.query(evalg.models.election.ElectionGroup).get(group_id)
        self.ballot_serializer = self._init_ballot_serializer(election_key)
        self.id2candidate = self._init_id2candidate()
        self.id2pollbook = self._init_id2pollbook()
        self.id2list = self._init_id2list()

    def _init_id2candidate(self):
        id2candidate = {}
        for election in self.group.elections:
            for candidate in election.candidates:
                id2candidate[str(candidate.id)] = candidate
        return id2candidate

    def _init_id2pollbook(self):
        id2pollbook = {}
        for election in self.group.elections:
            for pollbook in election.pollbooks:
                id2pollbook[str(pollbook.id)] = pollbook
        return id2pollbook

    def _init_id2list(self):
        id2list = {}
        for election in self.group.elections:
            for election_list in election.lists:
                id2list[str(election_list.id)] = election_list
        return id2list

    def _init_ballot_serializer(self, election_key):
        try:
            ballot_serializer = Base64NaClSerializer(
                election_private_key=election_key,
                election_public_key=self.group.public_key,
                backend_private_key=self.app_config.get("BACKEND_PRIVATE_KEY"),
                backend_public_key=self.app_config.get("BACKEND_PUBLIC_KEY"),
                envelope_padded_len=self.app_config.get("ENVELOPE_PADDED_LEN"),
            )
        except Exception as e:
            logger.error(e)
            capture_exception(e)
            return None
        return ballot_serializer

    def verify_election_key(self):
        serialized_test_ballot = self.ballot_serializer.serialize(dict(a=1, b=2))
        try:
            self.ballot_serializer.deserialize(serialized_test_ballot)
        except nacl.exceptions.CryptoError as e:
            logger.error(e)
            capture_exception(e)
            return False
        return True

    def log_start_count(self):
        utc_now = datetime.datetime.now(datetime.timezone.utc)

        db_row = ElectionGroupCount(
            group_id=self.group_id,
            initiated_at=utc_now,
        )
        self.session.add(db_row)
        self.session.commit()
        return db_row

    def log_finalize_count(self, db_row):
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        db_row.finished_at = utc_now

        self.session.add(db_row)
        self.session.commit()
        return db_row

    def get_ballots_query(self, pollbook_id):
        query = (
            self.session.query(Envelope)
            .join(Vote, and_(Vote.ballot_id == Envelope.id))
            .join(Voter, and_(Voter.id == Vote.voter_id))
            .filter(Voter.pollbook_id == pollbook_id, Voter.verified == True)
        )
        return query

    def deserialize_ballots(self):
        for election in self.group.elections:
            if election.status == "closed":
                election.ballots = []
                for pollbook in election.pollbooks:
                    pollbook.ballots = []
                    envelopes = self.get_ballots_query(pollbook.id).all()
                    for envelope in envelopes:
                        ballot_data = self.ballot_serializer.deserialize(
                            envelope.ballot_data
                        )
                        if election.type_str in ("sainte_lague", "uio_sainte_lague"):
                            ballot = ListBallot(
                                ballot_data,
                                self.id2pollbook,
                                self.id2list,
                                self.id2candidate,
                            )
                        else:
                            ballot = Ballot(
                                ballot_data, self.id2pollbook, self.id2candidate
                            )
                        pollbook.ballots.append(ballot)

    def process_for_count(self):
        for election in self.group.elections:
            if election.status == "closed":
                for pollbook in election.pollbooks:
                    set_pollbook_stats(pollbook)
                set_weight_per_pollbooks(election.pollbooks)

                election.ballots = []
                election.total_amount_ballots = 0
                election.total_amount_empty_ballots = 0
                election.total_amount_counting_ballots = 0

                for pollbook in election.pollbooks:
                    election.total_amount_ballots += pollbook.ballots_count
                    election.total_amount_empty_ballots += pollbook.empty_ballots_count
                    election.total_amount_counting_ballots += (
                        pollbook.counting_ballots_count
                    )
                    election.ballots.extend(pollbook.ballots)

    def generate_results(self, count, counted_by=None):
        for election in self.group.elections:
            if election.status == "closed":
                if election.type_str in ("sainte_lague", "uio_sainte_lague"):
                    result, protocol = party_list.get_result(election)
                    election_protocol_dict = protocol.to_dict()
                elif election.type_str == "uit_stv":
                    result, protocol = uitstv.get_result(election)
                    election_protocol_dict = protocol.to_dict()
                elif election.type_str == "positional_voting":
                    result, protocol = positional_voting.get_result(election)
                    election_protocol_dict = protocol.to_dict()
                else:
                    counter = Counter(
                        election, election.ballots, test_mode=self.test_mode
                    )
                    election_count_tree = counter.count()
                    election_path = election_count_tree.default_path

                    result = election_path.get_result().to_dict()
                    election_protocol_dict = election_path.get_protocol().to_dict()

                # insert the name of the one who triggered the counting
                election_protocol_dict["meta"]["counted_by"] = counted_by
                ballots = [ballot.ballot_data for ballot in election.ballots]

                pollbook_stats = {}
                for pollbook in election.pollbooks:
                    pollbook_stats[str(pollbook.id)] = {
                        "verified_voters_count": get_verified_voters_count(
                            self.session, pollbook.id
                        ),
                        "ballots_count": pollbook.ballots_count,
                        "counting_ballots_count": pollbook.counting_ballots_count,
                        "empty_ballots_count": pollbook.empty_ballots_count,
                    }

                db_row = ElectionResult(
                    election_id=election.id,
                    election_group_count_id=count.id,
                    ballots=ballots,
                    result=result,
                    election_protocol=election_protocol_dict,
                    pollbook_stats=pollbook_stats,
                )
                self.session.add(db_row)
                self.session.commit()
