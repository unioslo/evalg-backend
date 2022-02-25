"""Methods for adding, updating and deleting candidates."""
import logging
from typing import Optional
from sqlalchemy.orm.scoping import scoped_session

import evalg.models.election_list
from evalg.models.candidate import Candidate
from evalg.models.election_list import ElectionList

logger = logging.getLogger(__name__)


def remove_holes_in_priority(
    session: scoped_session, election_list: ElectionList
) -> None:
    """
    Remove any holes after a candidate is deleted

    1, 2, 4, 5 -> 1, 2, 3, 4
    4, 5, 6, 7 -> 1, 2, 3, 4
    1, 2, 3, 40 -> 1, 2, 3, 4
    """

    if len(election_list.candidates) == 0:
        return

    candidate_priorities = {c.priority: c for c in election_list.candidates}
    if len(election_list.candidates) < max(candidate_priorities.keys()):
        cur_priority = 1
        for old_priority in sorted(candidate_priorities.keys()):
            c = candidate_priorities[old_priority]
            c.priority = cur_priority
            cur_priority += 1
            session.add(c)
        session.commit()


def shift_candidate_priority(
    session: scoped_session,
    election_list: ElectionList,
    candidate: Candidate,
    old_priority: int,
) -> None:
    """
    Fixes the priority order after a list candidate update.

    If we change the priority of a candidate, we might need to
    reassign the other candidate to make the a valid candidate order.
    """

    if old_priority == candidate.priority:
        return None

    lookup_candidates = [x for x in election_list.candidates if x != candidate]
    if candidate.priority not in [x.priority for x in lookup_candidates]:
        return

    if candidate.priority < old_priority:
        # Move the candidate up in priority, bump the intermediate candidates down one step.
        for c in lookup_candidates:
            if c.priority >= candidate.priority and c.priority < old_priority:
                c.priority += 1
                session.add(c)
    else:
        # Move the candidate down in priority, bump the intermediate candidates up one step.
        for c in lookup_candidates:
            if old_priority < c.priority <= candidate.priority:
                c.priority -= 1
                session.add(c)

    session.commit()


def fix_priority_after_add(
    session: scoped_session,
    election_list: ElectionList,
    new_candidate: Candidate,
) -> None:
    """
    Fix the priority order then adding a new candidate to a list.

    exitsing_priorities = 1,2,3,4
    new_candidate_priority = 2

    Move the old priorities 2,3,4 -> 3,4,5
    """

    if not new_candidate.priority:
        new_candidate.priority = (
            max([c.priorities for c in election_list.candidates]) + 1
        )
        session.add(new_candidate)
        session.commit()
        return

    candidate_priorities = {
        c.priority: c for c in election_list.candidates if c != new_candidate
    }
    if new_candidate.priority in candidate_priorities.keys():
        candidates = [
            c
            for c in candidate_priorities.values()
            if c.priority >= new_candidate.priority
        ]
        for c in candidates:
            c.priority += 1
            session.add(c)
        session.commit()


def add_candidate(
    session: scoped_session,
    name: str,
    meta: dict,
    election_list_id: str,
    information_url: str,
    priority: int = 0,
    pre_cumulated: bool = False,
) -> bool:
    """Add a candidate to a election list."""
    election_list = session.query(evalg.models.election_list.ElectionList).get(
        election_list_id
    )
    if election_list.election.is_locked:
        # The election is ongoing or there are already votes
        logger.info(
            "Could not add candidate to election list. "
            "The election is locked. election_list %s",
            election_list_id,
        )
        return False
    candidate = evalg.models.candidate.Candidate(
        name=name,
        meta=meta,
        list_id=election_list.id,
        information_url=information_url,
        priority=priority,
        pre_cumulated=pre_cumulated,
    )
    session.add(candidate)
    session.commit()
    if election_list.election.meta["candidate_type"] == "party_list":
        fix_priority_after_add(session, election_list, candidate)
        remove_holes_in_priority(session, election_list)
    logger.info(
        "Added candidate %s to election list %s", candidate.id, election_list_id
    )
    return True


def delete_candidate(session: scoped_session, candidate_id: str) -> bool:
    """
    Delete a candidate.

    :param session: DB session
    :param candidate_id: candidate id
    :return: True if candidate is deleted, False else.
    """
    candidate = session.query(evalg.models.candidate.Candidate).get(candidate_id)
    if candidate.list.election.is_locked:
        logger.info("Can't delete candidate. The election is locked.")
        return False
    session.delete(candidate)
    session.commit()

    if candidate.list.election.meta["candidate_type"] == "party_list":
        remove_holes_in_priority(session, candidate.list)

    logger.info("Candidate %s deleted", candidate_id)
    return True


def update_candidate(
    session: scoped_session,
    name: str,
    meta: dict,
    candidate_id: str,
    election_list_id: str,
    priority: int = 0,
    pre_cumulated: bool = False,
    information_url: Optional[str] = None,
) -> bool:
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
    candidate = session.query(evalg.models.candidate.Candidate).get(candidate_id)
    if not candidate:
        logging.info(
            "Can't update candidate. No candidate with ID %s found", candidate_id
        )
        return False
    if candidate.list.election.is_locked and election_list_id != candidate.list_id:
        logger.info("Can't update candidate list-ID. The election is locked.")
        return False

    election_list = session.query(evalg.models.election_list.ElectionList).get(
        election_list_id
    )
    if election_list.election.is_locked:
        if election_list_id != candidate.list_id:
            logger.info(
                "Can't update candidate list-ID. " "The target election is locked."
            )
            return False

        elif priority != candidate.priority:
            logger.info(
                "Can't update candidate priority. " "The target election is locked."
            )
            return False

    old_priority = candidate.priority
    candidate.name = name
    candidate.meta.update(meta)
    candidate.list_id = election_list_id
    candidate.information_url = information_url
    candidate.priority = priority
    candidate.pre_cumulated = pre_cumulated
    session.add(candidate)
    session.commit()

    if election_list.election.meta["candidate_type"] == "party_list":
        shift_candidate_priority(session, election_list, candidate, old_priority)
        remove_holes_in_priority(session, election_list)

    logger.info("Candidate %s updated successfully", candidate_id)
    return True
