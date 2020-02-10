"""Methods for adding, updating and deleting candidates."""
import logging

import evalg.models.election_list

logger = logging.getLogger(__name__)


def add_candidate(session, name, meta, election_list_id, information_url):
    """Add a candidate to a election list."""
    election_list = session.query(
        evalg.models.election_list.ElectionList).get(election_list_id)
    if election_list.election.has_votes:
        # There are already votes for this election
        logger.info(
            'Could not add candidate to election list, there are votes in the '
            'election. election_list %s', election_list_id)
        return False
    candidate = evalg.models.candidate.Candidate(
        name=name,
        meta=meta,
        list_id=election_list.id,
        information_url=information_url)
    session.add(candidate)
    session.commit()
    logger.info('Added candidate %s to election list %s',
                candidate.id,
                election_list_id)
    return True


def delete_candidate(session, candidate_id):
    """
    Delete a candidate.

    :param session: DB session
    :param candidate_id: candidate id
    :return: True if candidate is deleted, false else.
    """
    candidate = session.query(evalg.models.candidate.Candidate).get(
        candidate_id
    )
    if candidate.list.election.has_votes:
        logger.info('Can\'t delete candidate, election has votes.')
        return False
    session.delete(candidate)
    session.commit()
    logger.info('Candidate %s deleted', candidate_id)
    return True


def update_candidate(session,
                     name,
                     meta,
                     candidate_id,
                     election_list_id,
                     information_url=None):
    """
    Update a candidate.

    :param session: DB session
    :param name: Candidate name
    :param meta: Candidate meta information dict, specified fields will be
        updated. Any other existing fields will be left untouched.
    :param candidate_id: Candidate id
    :param election_list_id: Election list id.
    :param information_url: Information url
    :return: True if update is successful, false else.
    """
    candidate = session.query(
        evalg.models.candidate.Candidate).get(candidate_id)
    if not candidate:
        logging.info('Can\'t update candidate. No candidate with ID %s found',
                     candidate_id)
        return False
    candidate.name = name
    candidate.meta.update(meta)
    candidate.list_id = election_list_id
    candidate.information_url = information_url
    session.add(candidate)
    session.commit()
    logger.info('Candidate %s updated successfully', candidate_id)
    return True
