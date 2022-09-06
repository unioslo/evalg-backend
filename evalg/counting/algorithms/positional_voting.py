import datetime
import decimal
import logging
import pytz
import random
from typing import Dict, List, Tuple, Any
from uuid import UUID

from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass

from evalg.counting import base
from evalg.models.election import Election, QuotaGroup
from evalg.models.candidate import Candidate

DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class Protocol(base.Protocol):
    """Poll Protocol"""

    def render(self, template: str = "protocol_positional_voting.tmpl"):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to be used
                         (default: protocol_list.tmpl)
        :type template: str

        :return: The rendered unicode text
        :rtype: str
        """
        return super().render(template=template)


def rank_candidates(
    candidates: List[Candidate], election_ballots: List[Any]
) -> Tuple[List[Candidate], Dict[UUID, float], bool]:
    """
    Count how many votes from ballots each candidate recieved and create a ranked list.

    :return: The ranked list of candidates, a dict with complete vote numbers for each candidate,
             and whether a random draw happened
    """
    logger.info("Counting votes and ranking candidates")
    candidate_vote_number = {cand.id: 0.0 for cand in candidates}
    for ballot in election_ballots:
        if len(candidates) < 3:
            if ballot.candidates:
                candidate_vote_number[ballot.candidates[0].id] += 1
        else:
            division = 1
            for cand in ballot.candidates:
                candidate_vote_number[cand.id] += 1 / division
                division += 2

    random_draw = False
    ranked_candidates = candidates.copy()
    vote_numbers = list(candidate_vote_number.values())
    if len(vote_numbers) != len(set(vote_numbers)):
        logger.info("Shuffling candidates due to someone having an equal vote number")
        random.shuffle(ranked_candidates)
        random_draw = True
    ranked_candidates.sort(key=lambda c: candidate_vote_number[c.id], reverse=True)
    return ranked_candidates, candidate_vote_number, random_draw


def get_other_quota_group(quotas: List[QuotaGroup], candidate: Candidate) -> QuotaGroup:
    """
    :return: The quota group `candidate` is not a member of
    :rtype: QuotaGroup
    Assumes that a candidate is only part of a single quota group.
    This should always be the case with gender quotas.
    """
    for quota in quotas:
        if candidate not in quota.members:
            return quota
    raise Exception("Candidate has no quota group they are not a member of")


def get_quota_group(quotas: List[QuotaGroup], candidate: Candidate) -> QuotaGroup:
    """
    :return: The quota group `candidate` is a member of
    :rtype: QuotaGroup
    Assumes that a candidate is only part of a single quota group.
    This should always be the case with gender quotas.
    """
    for quota in quotas:
        if candidate in quota.members:
            return quota
    raise Exception("Candidate is not member of any quota group")


def can_elect_candidate(
    candidate: Candidate,
    quota_elected: Dict[str, int],
    to_be_elected: int,
    quotas: List[QuotaGroup],
) -> bool:
    """
    :return: Whether the candidate can be elected when looking at quota rules
    :rtype: Boolean
    """
    other_quota = get_other_quota_group(quotas, candidate)
    return bool(
        other_quota.min_value - quota_elected[str(other_quota.name)] < to_be_elected
    )


def can_elect_substitute(
    candidate: Candidate,
    quota_elected: Dict[str, int],
    to_be_elected: int,
    quotas: List[QuotaGroup],
) -> bool:
    """
    :return: Whether the candidate can be elected when looking at quota rules
    :rtype: Boolean
    """
    other_quota = get_other_quota_group(quotas, candidate)
    return bool(
        other_quota.min_value_substitutes - quota_elected[str(other_quota.name)]
        < to_be_elected
    )


def follow_quota_rules(
    election: Election, ranked_candidates: List[Candidate]
) -> Tuple[List[Candidate], List[Candidate]]:
    logger.info(
        "Electing candidates and substitutes in accordance to gender quota rules"
    )
    quotas = election.quotas
    quota_elected = {str(q.name): 0 for q in quotas}
    elected = []
    to_be_elected = election.num_choosable
    for cand in ranked_candidates:
        if can_elect_candidate(cand, quota_elected, to_be_elected, quotas):
            elected.append(cand)
            quota_elected[str(get_quota_group(quotas, cand).name)] += 1
            to_be_elected -= 1
            if to_be_elected == 0:
                break

    if not "combined_substitute" in election.quota_names:
        logger.debug("Reseting count of elected in quotas before electing substitutes")
        quota_elected = {str(q.name): 0 for q in quotas}

    substitutes = []
    to_be_elected = election.num_substitutes
    for cand in ranked_candidates:
        if cand not in elected and can_elect_substitute(
            cand, quota_elected, to_be_elected, quotas
        ):
            substitutes.append(cand)
            quota_elected[str(get_quota_group(quotas, cand).name)] += 1
            to_be_elected -= 1
            if to_be_elected == 0:
                break

    return elected, substitutes


def get_result(election: Election) -> Tuple[Dict[str, Any], Protocol]:
    ranked_candidates, candidate_vote_number, random_draw = rank_candidates(
        List(election.candidates), election.ballots
    )

    if election.quotas:
        elected, substitutes = follow_quota_rules(election, ranked_candidates)
    else:
        num_candidates = election.num_choosable
        num_combined = num_candidates + election.num_substitutes
        elected = ranked_candidates[:num_candidates]
        substitutes = ranked_candidates[num_candidates:num_combined]

    result = create_result_dict(election, random_draw, elected, substitutes)
    protocol = get_protocol(
        election,
        ranked_candidates,
        elected,
        substitutes,
        candidate_vote_number,
        random_draw,
    )
    return result, protocol


def create_result_dict(
    election: Election,
    random_draw: bool,
    elected: List[Candidate],
    substitutes: List[Candidate],
) -> Dict[str, Any]:
    pollbook_meta = []
    for pollbook in election.pollbooks:
        pollbook_meta.append(
            {
                "id": str(pollbook.id),
                "ballots_count": pollbook.ballots_count,
                "empty_ballots_count": pollbook.empty_ballots_count,
            }
        )
    return {
        "meta": {
            "election_type": election.type_str,
            "pollbooks": pollbook_meta,
            "drawing": random_draw,
        },
        "regular_candidates": [str(cand.id) for cand in elected],
        "substitute_candidates": [str(cand.id) for cand in substitutes],
    }


def get_protocol(
    election: Election,
    ranked_candidates: List[Candidate],
    elected: List[Candidate],
    substitutes: List[Candidate],
    candidate_vote_number: Dict[UUID, float],
    random_draw: bool,
) -> Protocol:
    meta = {
        "election_id": str(election.id),
        "election_name": election.name,
        "election_type": election.type_str,
        "candidate_ids": [str(cand.id) for cand in election.candidates],
        "candidates": {
            str(candidate.id): candidate.name for candidate in election.candidates
        },
        "counted_at": datetime.datetime.now()
        .astimezone(pytz.timezone("Europe/Oslo"))
        .strftime("%Y-%m-%d %H:%M:%S"),
        "counted_by": None,
        "election_start": election.start.astimezone(
            pytz.timezone("Europe/Oslo")
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "election_end": election.end.astimezone(pytz.timezone("Europe/Oslo")).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "ballots_count": election.total_amount_ballots,
        "counting_ballots_count": election.total_amount_counting_ballots,
        "empty_ballots_count": election.total_amount_empty_ballots,
        "num_regular": election.num_choosable,
        "num_substitutes": election.num_substitutes,
        "ranked_candidates": [str(rc.id) for rc in ranked_candidates],
        "regular_candidates": [str(cand.id) for cand in elected],
        "substitute_candidates": [str(cand.id) for cand in substitutes],
        "candidate_vote_number": {
            str(key): value for key, value in candidate_vote_number.items()
        },
        "drawing": random_draw,
    }
    pollbook_meta = []
    pollbook_mappings = {}
    for pollbook in election.pollbooks:
        pollbook_mappings.update({str(pollbook.id): pollbook.name})
        if "scale_factor" not in meta:
            if hasattr(pollbook, "scale_factor"):
                meta["scale_factor"] = str(
                    pollbook.scale_factor.quantize(
                        decimal.Decimal("1.00"), decimal.ROUND_HALF_EVEN
                    )
                )
            else:
                meta["scale_factor"] = "1"
        pollbook_meta.append(
            {
                "id": str(pollbook.id),
                "name": pollbook.name,
                "ballots_count": pollbook.ballots_count,
                "counting_ballots_count": pollbook.counting_ballots_count,
                "empty_ballots_count": pollbook.empty_ballots_count,
                "weight": pollbook.weight,
                "weight_per_vote": str(pollbook.weight_per_vote),
                "weight_per_pollbook": str(pollbook.weight_per_pollbook),
            }
        )
    meta["pollbook_mappings"] = pollbook_mappings
    meta["pollbooks"] = pollbook_meta
    return Protocol(meta)
