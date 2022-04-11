"""Methods for adding, updating and deleting election lists."""
import logging

import evalg.models as em

logger = logging.getLogger(__name__)


def add_election_list(session, name, election_id, description, information_url):
    """
    Add an election_list to an election

    :param session: DB session
    :param name: list name, not None
    :param election_id: election id, not None
    :param description: description for the list
    :param information_url: url with information about the list
    :return: True if list is deleted, False else.
    """

    election = session.query(em.election.Election).get(election_id)
    if election.is_locked:
        logger.info(
            "Could not add election list to the election. "
            "The election is locked. election %s",
            election_id,
        )
        return False
    election_list = em.election_list.ElectionList(
        name=name,
        election_id=election.id,
        description=description,
        information_url=information_url,
    )
    session.add(election_list)
    session.commit()
    logger.info("Added election_list %s to election %s", election_list.id, election_id)
    return True


def delete_election_list(session, list_id):
    """
    Delete a list.

    :param session: DB session
    :param list_id: election list id
    :return: True if list is deleted, False else.
    """
    election_list = session.query(em.election_list.ElectionList).get(list_id)
    if election_list.election.is_locked:
        logger.info("Can't delete list. The election is locked.")
        return False
    session.delete(election_list)
    session.commit()
    logger.info("Candidate %s deleted", list_id)
    return True


def update_election_list(
    session, name, election_list_id, election_id, description=None, information_url=None
):
    """
    Update a list.

    :param session: DB session
    :param name: List name
    :param description: Description
    :param election_list_id: Election list id.
    :param election_id: Election id.
    :param information_url: Information url
    :return: True if update is successful, false else.
    """
    election_list = session.query(em.election_list.ElectionList).get(election_list_id)
    if not election_list:
        logging.info(
            "Can't update election list. No election list with ID %s found",
            election_list_id,
        )
        return False
    if election_id != election_list.election.id and election_list.election.is_locked:
        logger.info("Can't update election-id for the list. The election is locked.")
        return False
    election = session.query(em.election.Election).get(election_id)
    if election_id != election_list.election.id and election.is_locked:
        logger.info(
            "Can't update election-id for the list. " "The target election is locked."
        )
        return False
    election_list.name = name
    election_list.election_id = election_id
    election_list.description = description
    election_list.information_url = information_url
    session.add(election_list)
    session.commit()
    logger.info("Election list %s updated successfully", election_list_id)
    return True
