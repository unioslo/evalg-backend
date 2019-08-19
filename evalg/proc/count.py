"""Module for pre processing data and initiating count"""
import logging
import datetime
import decimal

import nacl.exceptions

from flask import current_app

from sqlalchemy.sql import and_

import evalg.database.query
from evalg.models.ballot import Envelope
from evalg.models.votes import Vote
from evalg.models.election_result import ElectionResult
from evalg.models.election_group_count import ElectionGroupCount
from evalg.models.voter import Voter
from evalg.proc.vote import get_verified_voters_count
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer
from evalg.counting.count import Counter

logger = logging.getLogger(__name__)


class Ballot:
    def __init__(self, ballot_data, id2pollbook, id2candidate):
        self.ballot_data = ballot_data
        self.pollbook = id2pollbook[ballot_data['pollbookId']]
        self.candidates = [id2candidate[id] for id in
                           ballot_data['rankedCandidateIds']]

    @property
    def raw_string(self):
        return ' '.join(
            [str(self.pollbook.id)] +
            [str(candidate.id) for candidate in self.candidates]
        )


def get_counting_ballots(ballots):
    return list(
        filter(
            lambda ballot: ballot.candidates != [],
            ballots
        )
    )


def get_empty_ballots(ballots):
    return list(
        filter(
            lambda ballot: ballot.candidates == [],
            ballots
        )
    )


def get_weight_per_vote(pollbook):
    if pollbook.counting_ballots_count == 0:
        return decimal.Decimal(0)
    return (decimal.Decimal(pollbook.weight) /
            decimal.Decimal(pollbook.counting_ballots_count))


def set_pollbook_stats(pollbook):
    pollbook.ballots_count = len(pollbook.ballots)
    pollbook.counting_ballots_count = len(
        get_counting_ballots(
            pollbook.ballots
        )
    )
    pollbook.empty_ballots_count = len(
        get_empty_ballots(
            pollbook.ballots
        )
    )
    pollbook.weight_per_vote = get_weight_per_vote(pollbook)


def set_weight_per_pollbook(pollbook, min_wpv):
    pollbook.weight_per_pollbook = pollbook.weight_per_vote / min_wpv


def set_weight_per_pollbooks(pollbooks):
    min_wpv = min(
        [pollbook.weight_per_vote for pollbook in pollbooks if
         pollbook.weight_per_vote],
        default=decimal.Decimal(1)
    )
    for pollbook in pollbooks:
        set_weight_per_pollbook(pollbook, min_wpv)


class ElectionGroupCounter:
    def __init__(self, session, group_id, election_key):
        self.app_config = current_app.config
        self.session = session
        self.group_id = group_id
        self.group = evalg.database.query.lookup(
            self.session,
            evalg.models.election.ElectionGroup,
            id=group_id
        )
        self.ballot_serializer = self._init_ballot_serializer(election_key)
        self.id2candidate = self._init_id2candidate()
        self.id2pollbook = self._init_id2pollbook()

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

    def _init_ballot_serializer(self, election_key):
        try:
            ballot_serializer = Base64NaClSerializer(
                election_private_key=election_key,
                election_public_key=self.group.public_key,
                backend_private_key=self.app_config.get('BACKEND_PRIVATE_KEY'),
                backend_public_key=self.app_config.get('BACKEND_PUBLIC_KEY'),
                envelope_padded_len=self.app_config.get('ENVELOPE_PADDED_LEN'),
            )
        except Exception as e:
            logger.error(e)
            return None
        return ballot_serializer

    def verify_election_key(self):
        serialized_test_ballot = self.ballot_serializer.serialize(
            dict(a=1, b=2)
        )
        try:
            self.ballot_serializer.deserialize(
                serialized_test_ballot)
        except nacl.exceptions.CryptoError as e:
            logger.error(e)
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
        query = self.session.query(
            Envelope
        ).join(
            Vote,
            and_(
                Vote.ballot_id == Envelope.id
            )
        ).join(
            Voter,
            and_(
                Voter.id == Vote.voter_id
            )
        ).filter(
            Voter.pollbook_id == pollbook_id,
            Voter.verified == True
        )
        return query

    def deserialize_ballots(self):
        for election in self.group.elections:
            if election.status == 'closed':
                election.ballots = []
                for pollbook in election.pollbooks:
                    pollbook.ballots = []
                    envelopes = self.get_ballots_query(pollbook.id).all()
                    for envelope in envelopes:
                        ballot_data = self.ballot_serializer.deserialize(
                            envelope.ballot_data
                        )
                        ballot = Ballot(
                            ballot_data,
                            self.id2pollbook,
                            self.id2candidate
                        )
                        pollbook.ballots.append(ballot)

    def process_for_count(self):
        for election in self.group.elections:
            if election.status == 'closed':
                for pollbook in election.pollbooks:
                    set_pollbook_stats(pollbook)
                set_weight_per_pollbooks(election.pollbooks)

                election.ballots = []
                election.total_amount_ballots = 0
                election.total_amount_empty_ballots = 0
                election.total_amount_counting_ballots = 0

                for pollbook in election.pollbooks:
                    election.total_amount_ballots += pollbook.ballots_count
                    election.total_amount_empty_ballots += (
                        pollbook.empty_ballots_count)
                    election.total_amount_counting_ballots += (
                        pollbook.counting_ballots_count)
                    election.ballots.extend(pollbook.ballots)

    def generate_results(self, count, counted_by=None):
        for election in self.group.elections:
            if election.status == 'closed':
                counter = Counter(election, election.ballots)
                election_count_tree = counter.count()
                election_path = election_count_tree.default_path

                result = election_path.get_result().to_dict()
                election_protocol_dict = election_path.get_protocol().to_dict()
                # insert the name of the one who triggered the counting
                election_protocol_dict['meta']['counted_by'] = counted_by
                ballots = [ballot.ballot_data for ballot in election.ballots]

                pollbook_stats = {}
                for pollbook in election.pollbooks:
                    pollbook_stats[str(pollbook.id)] = {
                        'verified_voters_count': get_verified_voters_count(
                            self.session,
                            pollbook.id
                        ),
                        'ballots_count': pollbook.ballots_count,
                        'counting_ballots_count':
                            pollbook.counting_ballots_count,
                        'empty_ballots_count': pollbook.empty_ballots_count
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
