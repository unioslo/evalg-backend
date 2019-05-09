"""This module implements interfaces for voting and getting vote statistics."""
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
from evalg.models.candidate import Candidate
from evalg.models.election_list import ElectionList
from evalg.models.person import PersonExternalId, Person
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer

logger = logging.getLogger(__name__)


class ElectionVotePolicy(object):
    """Helper class used to create and store ballots correctly."""

    def __init__(self, session):
        self.session = session
        config = current_app.config
        self._envelope_type = config.get('ENVELOPE_TYPE')
        self._backend_private_key = config.get('BACKEND_PRIVATE_KEY')
        self._envelope_padded_len = config.get('ENVELOPE_PADDED_LEN')

    def get_voter(self, voter_id):
        try:
            voter = evalg.database.query.lookup(self.session,
                                                evalg.models.voter.Voter,
                                                id=voter_id)
        except evalg.database.query.TooFewError:
            logger.error('Voter %r does not exist', voter_id)
            return
        return voter

    def verify_election_is_ongoing(self, voter):
        if not voter.pollbook.election.is_ongoing:
            logger.error('Can not vote, election is closed')
            return False
        return True

    def verify_candidates_exist(self, ranked_candidate_ids, election_id):
        if ranked_candidate_ids:
            query = self.session.query(
                 func.count(Candidate.id)
            ).join(
                ElectionList,
                and_(
                    ElectionList.id == Candidate.list_id
                )
            ).filter(
                Candidate.id.in_(ranked_candidate_ids),
                ElectionList.election_id == election_id
            )
            number_of_candidates = query.first()[0]

            if number_of_candidates < len(ranked_candidate_ids):
                return False
        return True

    def verify_ballot_content(self, ballot_data, election_id):
        ranked_candidate_ids = ballot_data['rankedCandidateIds']
        if ranked_candidate_ids and ballot_data['isBlankVote']:
            logger.error('A blank vote can not contain preferred candidates')
            return False
        if not self.verify_candidates_exist(ranked_candidate_ids, election_id):
            logger.error('Selected candidate(s) does not exist (%r)',
                         ranked_candidate_ids)
            return False
        return True

    @property
    def envelope_type(self):
        """
        Envelope type in use to serialize ballots.

        Currently not used.
        """
        return self._envelope_type

    @property
    def ballot_type(self):
        """
        Ballot type.

        Is this in use?
        TODO: Implement, get this from the election group maybe?
        """
        return 'test_ballot'

    def make_ballot(self, ballot_data, election_public_key):
        """Create a envelope object with containing the serialized ballot."""
        # Future work: create serializer factory.
        serializer = Base64NaClSerializer(
            backend_private_key=self._backend_private_key,
            election_public_key=election_public_key,
            envelop_padded_len=self._envelope_padded_len,
        )
        ballot = Envelope(
            envelope_type=self.envelope_type,
            ballot_type=self.ballot_type,
            ballot_data=serializer.serialize(ballot_data)
        )
        return ballot

    def make_vote(self, voter, envelope):
        """Create a Vote object mapping a envelope to a voter."""
        vote = evalg.database.query.get_or_create(
            self.session, Vote, voter_id=voter.id)
        vote.ballot_id = envelope.id
        return vote

    def add_vote(self, voter, ballot_data):
        """Add a vote to a given election."""
        logger.info("Adding vote in election/pollbook %r/%r",
                    voter.pollbook.election, voter.pollbook)

        election_public_key = voter.pollbook.election.election_group.public_key
        if not election_public_key:
            raise Exception('Election key is missing.')

        envelope = self.make_ballot(ballot_data, election_public_key)
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
