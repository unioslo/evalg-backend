"""
This module implements interfaces for voting and getting vote statistics.
"""
import collections
import logging

from sqlalchemy.sql import and_, select, func

import evalg.database.query
from evalg.models.ballot import Envelope
from evalg.models.pollbook import PollBook
from evalg.models.voter import Voter
from evalg.models.votes import Vote
from evalg.models.person import PersonExternalId

logger = logging.getLogger(__name__)


class ElectionVotePolicy(object):
    """
    """

    def __init__(self, session):
        self.session = session

    @property
    def envelope_type(self):
        return 'test_envelope'

    @property
    def ballot_type(self):
        return 'test_ballot'

    def make_ballot(self, ballot_data):
        """
        :type election: evalg.models.election.Election
        :type ballot_data: str

        :rtype: evalg.models.ballot.Envelope

        """
        # TODO: Build a Ballot object and serialize.
        ballot_content = repr(ballot_data)

        ballot = Envelope(
            envelope_type=self.envelope_type,
            ballot_type=self.ballot_type,
            ballot_data=ballot_content,
        )
        return ballot

    def make_vote(self, voter, envelope):
        """
        Make a Vote object.

        :type voter: evalg.models.voter.Voter
        :type envelope: evalg.models.ballot.Envelope
        """
        vote = evalg.database.query.get_or_create(
            self.session, Vote, voter_id=voter.id)

        vote.ballot_id = envelope.id
        return vote

    def sign_ballot(self, envelope):
        """
        Sign ballot for an election.

        :type election: evalg.models.election.Election
        :type ballot: evalg.models.ballot.Envelope
        """
        # TODO: Get election key
        key = ''

        # Sign serialized ballot.
        envelope.sign(key)

    def add_vote(self, voter, ballot_data):
        """
        Add a vote for a given election.

        :type election: evalg.models.election.Election
        :type ballot: evalg.models.ballot.Envelope
        """
        logger.info("Adding vote in election/pollbook %r/%r",
                    voter.pollbook.election, voter.pollbook)

        if not voter.pollbook.election.is_ongoing:
            raise Exception('inactive election')

        envelope = self.make_ballot(ballot_data)
        self.session.add(envelope)
        self.session.flush()

        logger.info("Stored ballot %r", envelope)

        vote = self.make_vote(voter, envelope)
        self.session.add(vote)
        self.session.flush()

        logger.info("Stored vote %r", vote)
        return vote


def get_election_vote_counts(session, election):
    """
    Get a dict of vote counts for the election.

    The votes are grouped by

    approved
        Votes from voters that are ``verified``

    need_approval
        Votes from voters that are ``manual`` and not ``verified``

    omitted
        Votes from voters that are not ``manual`` and not ``verified``
    """
    voters_subq = select([Voter.id]).where(
        Voter.pollbook_id.in_(
            select([PollBook.id]).where(
                PollBook.election_id == election.id)))
    query = session.query(
        Voter.manual,
        Voter.verified,
        func.count(Vote.ballot_id)
    ).join(
        Vote
    ).filter(
        Voter.id.in_(voters_subq)
    ).group_by(
        Voter.manual,
        Voter.verified
    )
    keys = {
        (True, True): 'approved',
        (True, False): 'need_approval',
        (False, True): 'approved',
        (False, False): 'omitted',
    }
    count = collections.Counter()
    for m, v, c in query.all():
        key = keys[m, v]
        count[key] += c
    return count


def get_votes_for_person(session, person):
    """
    Get all voters for a person, in prioritized order.
    """
    vote_query = session.query(
        Vote
    ).join(
        Voter
    ).join(
        PollBook
    ).join(
        PersonExternalId,
        and_(
            Voter.id_type == PersonExternalId.id_type,
            Voter.id_value == PersonExternalId.id_value)
    ).filter(
        PersonExternalId.person_id == person.id
    ).order_by(
        PollBook.priority
    )
    return vote_query
