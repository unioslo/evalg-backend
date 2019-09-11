"""
This module implements functionality related to pollbooks

This includes:

- Adding a voter to a pollbook
- Querying the database for information about a pollbook and voters

"""
import logging

from sqlalchemy.sql import and_

import evalg.database.query
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
