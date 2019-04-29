"""
This module implements interfaces for voting and getting vote statistics.
"""
import collections
import logging

from flask import current_app
from sqlalchemy.sql import and_, select, func

import evalg.database.query
from evalg.models.ballot import Envelope
from evalg.models.pollbook import PollBook
from evalg.models.election import ElectionGroup, Election
from evalg.models.voter import Voter, VERIFIED_STATUS_MAP
from evalg.models.votes import Vote
from evalg.models.person import PersonExternalId, Person
from evalg.serializer import Base64NaClSerializer

logger = logging.getLogger(__name__)


class ElectionVotePolicy(object):
    """
    """

    def __init__(self, session):
        self.session = session
        config = current_app.config
        self._envelope_type = config.get('ENVELOPE_TYPE')
        self._backend_private_key = config.get('BACKEND_PRIVATE_KEY')

    @property
    def envelope_type(self):
        return self._envelope_type

    @property
    def ballot_type(self):
        # TODO: get from ballot?
        return 'test_ballot'

    def make_ballot(self, ballot_data, voter, election_public_key):
        """
        :type election: evalg.models.election.Election
        :type ballot_data: str

        :rtype: evalg.models.ballot.Envelope

        """
        # TODO: Build a Ballot object and serialize.
        ballot_content = repr(ballot_data)

        # TODO: create factory?

        # Get keys

        # TODO: verify ballot_data content

        # TODO: get election key

        serializer = Base64NaClSerializer(
            backend_private_key=self._backend_private_key,
            election_public_key=election_public_key,
        )

        ballot = Envelope(
            envelope_type=self.envelope_type,
            ballot_type=self.ballot_type,
            ballot_data=serializer.serialize(ballot_data)
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

        # TODO: verify ballot data

        # TODO: get public key

        election_public_key = voter.pollbook.election.election_group.public_key

        if not election_public_key:
            raise Exception('Election is missing key')

        envelope = self.make_ballot(ballot_data,
                                    voter,
                                    election_public_key)

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

    The votes are grouped by the voters' ``verified_status``
    """
    voters_subq = select([Voter.id]).where(
        Voter.pollbook_id.in_(
            select([PollBook.id]).where(
                PollBook.election_id == election.id)))
    query = session.query(
        Voter.self_added,
        Voter.reviewed,
        Voter.verified,
        func.count(Vote.ballot_id)
    ).join(
        Vote
    ).filter(
        Voter.id.in_(voters_subq)
    ).group_by(
        Voter.self_added,
        Voter.reviewed,
        Voter.verified,
    )

    count = collections.Counter()
    for self_added, reviewed, verified, votes in query.all():
        name = VERIFIED_STATUS_MAP[(self_added, reviewed, verified)].name
        count[name.lower()] += votes
    total = 0
    for votes in count.values():
        total += votes
    count['total'] = total
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


def get_person_for_voter(session, voter):
    query = session.query(
        Person
    ).join(
        PersonExternalId,
        and_(
            Person.id == PersonExternalId.person_id,
        )
    ).join(
        Voter,
        and_(
            Voter.id_type == PersonExternalId.id_type,
            Voter.id_value == PersonExternalId.id_value
        )
    ).filter(
        Voter.id == voter.id
    ).first()

    return query


def get_voters_for_election_group(session, election_group_id, self_added=None):
    query = session.query(
        Voter
    ).join(
        PollBook,
        and_(
            Voter.pollbook_id == PollBook.id
        )
    ).join(
        Election,
        and_(
            PollBook.election_id == Election.id
        )
    ).join(
        ElectionGroup,
        and_(
            Election.group_id == election_group_id
        )
    )
    if self_added is not None:
        query = query.filter(Voter.self_added == self_added)
    return query


def get_voters_by_self_added(session, pollbook_id, self_added):
    query = session.query(
        Voter
    ).filter(
        Voter.self_added == self_added,
        Voter.pollbook_id == pollbook_id
    )
    return query
