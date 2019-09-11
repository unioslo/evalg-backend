"""
This module implements functionality related to pollbooks

This includes:

- Adding a voter to a pollbook
- Querying the database for information about a pollbook and voters

"""
import logging

from sqlalchemy import and_, func

import evalg.database.query
from evalg.models.election import Election, ElectionGroup
from evalg.models.person import Person, PersonExternalId
from evalg.models.pollbook import PollBook
from evalg.models.votes import Vote
from evalg.models.voter import Voter

logger = logging.getLogger(__name__)


def get_voters_for_person(session, person, election=None):
    """
    Get a query for fetching all voters for a person, in prioritized order.

    :type person: evalg.models.person.Person
    :param person: The person to fetch voter objects for

    :type election: evalg.models.election.Election
    :param election:
        If given, only include voter objects for the given election.

    :rtype: evalg.models.voter.Voter
    """
    if election is None:
        cond = PersonExternalId.person_id == person.id
    else:
        cond = and_(
            PersonExternalId.person_id == person.id,
            Voter.pollbook_id.in_(p.id for p in election.pollbooks))

    voter_query = session.query(
        Voter
    ).join(
        PersonExternalId,
        and_(
            Voter.id_type == PersonExternalId.id_type,
            Voter.id_value == PersonExternalId.id_value)
    ).join(
        PollBook
    ).filter(
        cond
    ).order_by(
        PollBook.priority
    )
    return voter_query


def get_voters_for_id(session, id_type, id_value, election=None):
    if election is None:
        cond = and_(
            Voter.id_type == id_type,
            Voter.id_value == id_value)
    else:
        cond = and_(
            Voter.id_type == id_type,
            Voter.id_value == id_value,
            Voter.pollbook_id.in_(p.id for p in election.pollbooks))

    voter_query = session.query(
        Voter
    ).join(
        PollBook
    ).filter(
        cond
    ).order_by(
        PollBook.priority
    )
    return voter_query


def get_person_for_id(session, id_type, id_value):
    person_query = session.query(
        Person
    ).join(
        PersonExternalId
    ).filter(
        PersonExternalId.id_type == id_type,
        PersonExternalId.id_value == id_value,
    )
    return person_query


def get_voters_with_vote_in_pollbook(session, pollbook_id):
    voters = session.query(
        Voter
    ).outerjoin(
        Vote
    ).filter(
        and_(
            ~ Vote.voter_id.is_(None),
            Voter.verified.is_(True),
            Voter.pollbook_id == pollbook_id
        )
    ).all()
    return voters


def get_voters_without_vote_in_pollbook(session, pollbook_id):
    voters = session.query(
        Voter
    ).outerjoin(
        Vote
    ).filter(
        and_(
            Vote.voter_id.is_(None),
            Voter.verified.is_(True),
            Voter.pollbook_id == pollbook_id
        )
    ).all()

    return voters


class ElectionVoterPolicy(object):
    def __init__(self, session):
        self.session = session

    def add_voter_id(self, pollbook, id_type, id_value,
                     self_added=True, reason=None):
        """
        Add a voter to a pollbook for a given person object.
        """

        voter = self.get_voter_id(pollbook, id_type, id_value)

        if voter:
            raise ValueError('voter already exists in pollbook')

        voter = Voter(
            pollbook_id=pollbook.id,
            id_type=id_type,
            id_value=id_value,
            self_added=self_added,
            reviewed=False,
            verified=(not self_added),
            reason=reason,
        )

        self.session.add(voter)
        self.session.flush()
        logger.info('added voter %r', voter)
        return voter

    def add_voter(self, pollbook, person, self_added=True, reason=None):
        """
        Add a voter to a pollbook for a given person object.
        """
        voter = self.get_voter(pollbook, person)

        if voter:
            return voter

        id_obj = person.get_preferred_id()

        if not id_obj:
            raise ValueError('no valid external ids available for %r'
                             % (person, ))

        voter = Voter(
            pollbook_id=pollbook.id,
            id_type=id_obj.id_type,
            id_value=id_obj.id_value,
            self_added=self_added,
            reviewed=False,
            verified=(not self_added),
            reason=reason,
        )

        self.session.add(voter)
        self.session.flush()
        logger.info('added voter %r', voter)
        return voter

    def get_voter_id(self, pollbook, id_type, id_value):
        query = get_voters_for_id(self.session, id_type, id_value,
                                  election=pollbook.election)
        voter = query.filter(Voter.pollbook_id == pollbook.id).first()
        return voter

    def get_voter(self, pollbook, person):
        """
        Get voter for a given person in a given pollbook.
        """
        query = get_voters_for_person(self.session, person,
                                      election=pollbook.election)
        voter = query.filter(Voter.pollbook_id == pollbook.id).first()
        return voter


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


def get_voters_in_election_group(session, election_group_id, self_added=None,
                                 reviewed=None, verified=None,
                                 has_voted=None):
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
    if reviewed is not None:
        query = query.filter(Voter.reviewed == reviewed)
    if verified is not None:
        query = query.filter(Voter.verified == verified)
    if has_voted is not None:
        query = query.join(
            Vote,
            and_(
                Voter.id == Vote.voter_id
            )
        ).group_by(
            Voter.id
        )
        if has_voted:
            query = query.having(func.count(Vote.ballot_id) > 0)
        else:
            query = query.having(func.count(Vote.ballot_id) == 0)
    return query


def get_voters_by_self_added(session, pollbook_id, self_added):
    query = session.query(
        Voter
    ).filter(
        Voter.self_added == self_added,
        Voter.pollbook_id == pollbook_id
    )
    return query


def get_verified_voters_count(session, pollbook_id):
    return session.query(
        func.count(Voter.id)
    ).filter(
        Voter.pollbook_id == pollbook_id,
        Voter.verified,
    ).scalar()


def get_verified_voters_with_votes_count(session, pollbook_id):
    return session.query(
        func.count(Voter.id)
    ).filter(
        Voter.pollbook_id == pollbook_id,
        Voter.verified,
        Voter.votes
    ).scalar()


def get_persons_with_multiple_verified_voters(session, election_group_id):
    """Get persons who have more than one verified voter

    :param election_group_id: the election group to look for voters in
    :return: a query object where each row consists of a person and one of the
        person's voters.
    """
    s_election_group_voters = get_voters_in_election_group(
        session,
        election_group_id,
        verified=True,
        has_voted=True
    ).subquery()

    s_election_group_voter_ids = session.query(
        s_election_group_voters.c.id
    ).subquery()

    s_voting_persons = session.query(
        PersonExternalId.person_id,
        func.count(Voter.id).label('voter_count')
    ).join(
        Voter,
        and_(
            Voter.id_type == PersonExternalId.id_type,
            Voter.id_value == PersonExternalId.id_value,
        )
    ).filter(
        Voter.id.in_(s_election_group_voter_ids)
    ).group_by(
        PersonExternalId.person_id
    ).subquery()

    s_persons_with_multiple_votes = session.query(
        s_voting_persons.c.person_id
    ).filter(
        s_voting_persons.c.voter_count > 1
    ).subquery()

    query = session.query(Person, Voter).join(
        PersonExternalId,
        and_(
            Person.id == PersonExternalId.person_id
        )
    ).join(
        Voter,
        and_(
            Voter.id_type == PersonExternalId.id_type,
            Voter.id_value == PersonExternalId.id_value,
        )
    ).filter(
        PersonExternalId.person_id.in_(s_persons_with_multiple_votes)
    ).filter(
        Voter.id.in_(s_election_group_voter_ids)
    ).order_by(
        PersonExternalId.person_id
    )

    return query
