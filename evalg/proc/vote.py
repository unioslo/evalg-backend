"""
This module implements interfaces for voting and getting vote statistics.
"""
import logging

from sqlalchemy.sql import and_, select, func

import evalg.database.query
from evalg.models.ballot import Envelope
from evalg.models.pollbook import PollBook
from evalg.models.voter import Voter
from evalg.models.votes import Vote

logger = logging.getLogger(__name__)


class ElectionVotePolicy(object):
    """
    """

    acceptable_voter_status = ('imported', 'added', 'approved')

    def __init__(self, session, election):
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

        if voter.voter_status_id not in self.acceptable_voter_status:
            raise Exception('invalid voter status %r' %
                            (voter.voter_status_id,))

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
    Get a dict of vote count per voter_status in an election.
    """
    voters_subq = select([Voter.id]).where(
        Voter.pollbook_id.in_(
            select([PollBook.id]).where(
                PollBook.election_id == election.id)))
    query = session.query(
        Voter.voter_status_id,
        func.count(Vote.ballot_id)
    ).join(
        Vote
    ).filter(
        Voter.id.in_(voters_subq)
    ).group_by(
        Voter.voter_status_id
    )
    return dict(query.all())


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
    ).filter(
        Voter.person_id == person.id
    ).order_by(
        PollBook.priority
    )
    return vote_query
