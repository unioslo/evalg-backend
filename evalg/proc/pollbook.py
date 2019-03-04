"""
This module implements pollbook maintenance.

This includes:

- TODO: Updating the pollbook from sources
- Manually "moving" a voter from one pollbook to another

"""
import logging

from sqlalchemy.sql import and_

import evalg.database.query
from evalg.models.person import Person, PersonExternalId
from evalg.models.pollbook import PollBook
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
        PersonExternalId.id_value == id_type,
    )
    return person_query


def get_voter(session, voter_id):
    """
    Get a voter object by ``Voter.id``.
    """
    return evalg.database.query.lookup(
        session,
        evalg.models.voter.Voter,
        id=voter_id)


class ElectionVoterPolicy(object):
    """
    TODO:

    This is super messy. Our database model is not made for this.
    """

    preferred_ids = ('feide_id', 'nin')

    def __init__(self, session):
        self.session = session

    def add_voter_id(self, pollbook, id_type, id_value,
                     manual=True, reason=None):
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
            manual=manual,
            verified=(not manual),
            reason=reason,
        )

        self.session.add(voter)
        self.session.flush()
        logger.info('added voter %r', voter)
        return voter

    def add_voter(self, pollbook, person, manual=True, reason=None):
        """
        Add a voter to a pollbook for a given person object.
        """
        voter = self.get_voter(pollbook, person)

        if voter:
            raise ValueError('voter already exists in pollbook')

        id_obj = person.get_preferred_id(*self.preferred_ids)

        if not id_obj:
            raise ValueError('no valid external ids available for %r'
                             % (person, ))

        voter = Voter(
            pollbook_id=pollbook.id,
            id_type=id_obj.id_type,
            id_value=id_obj.id_value,
            manual=manual,
            verified=(not manual),
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
