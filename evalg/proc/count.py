"""
This module implements counting of votes

"""
import logging
import nacl.exceptions
import datetime

from sqlalchemy.sql import and_
from flask import current_app

import evalg.database.query
from evalg.models.ballot import Envelope
from evalg.models.votes import Vote
from evalg.models.election_group_count import ElectionGroupCount
from evalg.models.voter import Voter
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer
from collections import defaultdict
logger = logging.getLogger(__name__)


def verify_election_key(ballot_serializer):
    serialized_test_ballot = ballot_serializer.serialize(
        dict(a=1, b=2)
    )
    try:
        ballot_serializer.deserialize(
            serialized_test_ballot)
    except nacl.exceptions.CryptoError as e:
        logger.error(e)
        return False
    return True


class ElectionGroupCounter(object):
    def __init__(self, session, group_id):
        self.app_config = current_app.config
        self.session = session
        self.group_id = group_id
        self.group = evalg.database.query.lookup(
            self.session,
            evalg.models.election.ElectionGroup,
            id=group_id
        )

    def verify_election_statuses(self):
        for election in self.group.elections:
            if election.status not in ('closed', 'inactive'):
                logger.error(Exception('Election(s) in election group not '
                                       'closed'))
                return False
        return True

    def get_ballot_serializer(self, election_key):
        try:
            ballot_serializer = Base64NaClSerializer(
                election_private_key=election_key,
                election_public_key=self.group.public_key,
                backend_private_key=self.app_config.BACKEND_PRIVATE_KEY,
                backend_public_key=self.app_config.BACKEND_PUBLIC_KEY,
                envelope_padded_len=self.app_config.ENVELOPE_PADDED_LEN,
            )
        except Exception as e:
            logger.error(e)
            return None
        return ballot_serializer

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
            Voter.pollbook_id == pollbook_id
        )
        return query

    def deserialize_ballots(self, ballot_serializer):
        election_id2ballots = defaultdict(list)
        for election in self.group.elections:
            for pollbook in election.pollbooks:
                envelopes = self.get_ballots_query(pollbook.id).all()
                for envelope in envelopes:
                    ballot_data = ballot_serializer.deserialize(
                        envelope.ballot_data
                    )
                    election_id2ballots[election.id].append(ballot_data)

        logger.debug(election_id2ballots)
        return election_id2ballots

    # TODO: replace this with counting algorithm
    def count(self, election2ballots):
        pass
