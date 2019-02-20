"""
This module implements pollbook maintenance.

This includes:

- TODO: Updating the pollbook from sources
- Manually "moving" a voter from one pollbook to another

"""
import logging

from sqlalchemy.sql import and_

import evalg.database.query
from evalg.models.voter import Voter
from evalg.models.pollbook import PollBook

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
        cond = Voter.person_id == person.id
    else:
        cond = and_(
            Voter.person_id == person.id,
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

    statuses = ('imported', 'accepted', 'added', 'deleted')
    status_ok = ('imported', 'accepted', 'added')
    status_user_added = 'added'
    status_default = status_user_added

    def __init__(self, session):
        self.session = session

    def add_voter(self, pollbook, person, status=status_default, reason=None):
        """
        Add a voter to a pollbook for a given person object.
        """
        voter = self.get_voter(pollbook, person)

        if status not in self.statuses:
            raise ValueError('invalid status %r, must be one of %r'
                             % (status, self.statuses))

        if status == self.status_user_added and not reason:
            # Not *really* a ValueError?
            raise ValueError('must provide reason for voter status %r' %
                             (status, ))

        if voter:
            if voter.voter_status_id in self.status_ok:
                # Not *really* a ValueError?
                raise ValueError('voter already exists with status %r' %
                                 (voter.voter_status_id, ))
            logger.debug('re-enable voter %r, status %r -> %r',
                         voter, voter.voter_status_id, status)
            voter.voter_status_id = status
            if reason:
                voter.reason = reason
        else:
            voter = Voter(
                pollbook_id=pollbook.id,
                person_id=person.id,
                voter_status_id=status,
                reason=reason,
            )

        self.session.add(voter)
        self.session.flush()
        logger.info('added voter %r with status %r',
                    voter, voter.voter_status_id)
        return voter

    def get_voter(self, pollbook, person):
        """
        Get voter for a given person in a given pollbook.
        """
        query = get_voters_for_person(self.session, person,
                                      election=pollbook.election)
        voter = query.filter(Voter.pollbook_id == pollbook.id).first()
        return voter
