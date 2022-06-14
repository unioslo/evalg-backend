import datetime
import logging
import pytz
import random
import uuid

from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass

from evalg.counting import base

DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class Protocol(base.Protocol):
    """Poll Protocol"""

    # TODO: enten ikke bruk dette eller lag init her som gjør get_protocol unødvendig

    def render(self, template="protocol_uitstv.tmpl"):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to be used
                         (default: protocol_list.tmpl)
        :type template: str

        :return: The rendered unicode text
        :rtype: str
        """
        return super().render(template=template)


@dataclass
class Candidate:
    db_id: uuid.UUID
    name: str
    ballots: list
    vote_number: float = 0.0
    eliminated: bool = False

    def __eq__(self, other):
        return self.db_id == other.db_id

    def __lt__(self, other):
        return self.vote_number < other.vote_number

    def transfer_votes(self, elect_number, eliminated=False):
        if eliminated:
            weight_factor = 1
        else:
            weight_factor = 1 - elect_number / self.vote_number
        transfered_to = defaultdict(int)

        for ballot in self.ballots:
            ballot.weight *= weight_factor
            next_candidate = ballot.next_candidate()
            if next_candidate:
                transfered_to[next_candidate.name] += ballot.weight
                next_candidate.ballots.append(ballot)
                next_candidate.vote_number += ballot.weight
            else:
                transfered_to["ingen"] += ballot.weight

        transfer_protocol = {
            "type": "vote_transfer",
            "transfer_from": self.name,
            "num_votes": self.vote_number,
            "weight_factor": weight_factor,
            "transfered_to": transfered_to,
        }
        return transfer_protocol


@dataclass
class Ballot:
    candidates: list
    current_candidate = 0
    weight: float = 1.0

    def next_candidate(self):
        self.current_candidate += 1
        try:
            next_candidate = self.candidates[self.current_candidate]
            if not next_candidate.eliminated:
                return next_candidate
            else:
                return self.next_candidate()
        except IndexError:
            pass
        return None


def get_candidates_with_ballots(election_candidates, election_ballots):
    id2candidates = {}
    for candidate in election_candidates:
        id2candidates[candidate.id] = Candidate(
            db_id=candidate.id,
            name=candidate.name,
            ballots=[],
        )

    for ballot in election_ballots:
        if ballot.candidates:
            candidate = id2candidates[ballot.candidates[0].id]
            candidate.ballots.append(
                Ballot([id2candidates[c.id] for c in ballot.candidates])
            )
            candidate.vote_number += 1

    return list(id2candidates.values())


def count(possible_candidates, seats, elect_number):
    protocol_events = []
    elected = []
    while len(elected) < seats:

        vote_numbers = [c.vote_number for c in possible_candidates]
        if len(vote_numbers) != len(set(vote_numbers)):
            protocol_events.append({ "type": "random_sort" })
            random.shuffle(possible_candidates)

        possible_candidates.sort(reverse=True)
        protocol_events.append(
            {
                "type": "status",
                "info": [
                    {"name": c.name, "votes": c.vote_number}
                    for c in possible_candidates
                ],
            }
        )

        if len(possible_candidates) <= seats - len(elected):
            elected.extend(possible_candidates)
            protocol_events.append(
                {
                    "type": "elect_all_remaining",
                    "info": [{"name": c.name} for c in possible_candidates],
                }
            )
            break

        electable = [
            candidate
            for candidate in possible_candidates
            if candidate.vote_number >= elect_number
        ]
        if electable:
            for candidate in electable:
                protocol_events.append(
                    {
                        "type": "elect_single",
                        "name": candidate.name,
                        "votes": candidate.vote_number,
                    }
                )
                possible_candidates.remove(candidate)
                candidate.eliminated = True
                elected.append(candidate)
            for candidate in electable:
                transfer_protocol = candidate.transfer_votes(elect_number, False)
                protocol_events.append(transfer_protocol)
        else:
            candidate = possible_candidates.pop()
            protocol_events.append(
                {
                    "type": "eliminate",
                    "name": candidate.name,
                    "votes": candidate.vote_number,
                }
            )
            candidate.eliminated = True
            transfer_protocol = candidate.transfer_votes(elect_number, True)
            protocol_events.append(transfer_protocol)
    return elected, protocol_events


def rank_candidates(candidates, amount_of_counting_ballots):
    ranked_candidates = []
    ranking_protocol = []
    for seat in range(1, len(candidates) + 1):
        elect_number = int(1 + (amount_of_counting_ballots * 100 / (seat + 1))) / 100
        elected, count_events = count(deepcopy(candidates), seat, elect_number)
        for elected_cand in elected:
            if elected_cand not in ranked_candidates:
                count_events.append(
                    {
                        "type": "rank_candidate",
                        "name": elected_cand.name,
                        "rank": seat,
                    }
                )
                ranked_candidates.append(elected_cand)
                break
        ranking_protocol.append(count_events)
    return ranked_candidates, ranking_protocol


def get_result(election):
    candidates = get_candidates_with_ballots(election.candidates, election.ballots)
    ranked_candidates, ranking_protocol = rank_candidates(
        candidates, election.total_amount_counting_ballots
    )
    result = {
        "meta": {"election_type": election.type_str},
        "ranked_candidates": ranked_candidates,
    }
    protocol = get_protocol(election, ranking_protocol, ranked_candidates)
    return result, protocol


def get_protocol(election, counting_rounds, ranked_candidates):
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
        "ranked_candidates": ranked_candidates,
        "counting_rounds": counting_rounds,
    }
    return Protocol(meta)
