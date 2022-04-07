import datetime
import logging
import pytz
import random

from evalg.counting import base

DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)
# TODO: logging sammen med protokoll? Kanskje en holder til en del


class Protocol(base.Protocol):
    """Poll Protocol"""

    # TODO: enten ikke bruk dette eller lag init her som gjør get_protocol unødvendig

    def render(self, template='protocol_list.tmpl'):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to be used
                         (default: protocol_list.tmpl)
        :type template: str

        :return: The rendered unicode text
        :rtype: str
        """
        return super().render(template=template)


def get_list_counts(election_lists, ballots, num_choosable, pre_cumulate_weight):
    """
    Get votes for people and lists
    person votes for each person chosen and list votes based on number of person votes
    """
    person_votes = {}
    list_votes = {}
    for election_list in election_lists:
        person_votes[election_list.id] = {
            candidate.id: 0 for candidate in election_list.candidates
        }
        list_votes[election_list.id] = 0

    for ballot in ballots:
        list_votes[ballot.chosen_list.id] += num_choosable - len(
            ballot.personal_votes_other
        )

        for vote in ballot.personal_votes_same:
            # Kan vurdere å sjekke at antall er ok her? Hvis det ikke fikses på forhånd (det er nok best å gjøre før)
            if vote["cumulated"]:
                person_votes[ballot.chosen_list.id][vote["candidate"].id] += 2
            else:
                person_votes[ballot.chosen_list.id][vote["candidate"].id] += 1

        for other_vote in ballot.personal_votes_other:
            list_votes[other_vote["list"].id] += 1
            person_votes[other_vote["list"].id][other_vote["candidate"].id] += 1

        for candidate in ballot.chosen_list.candidates:
            if candidate.pre_cumulated:
                # Gjør noe sjekk her på at personen ikke er strøket? Dersom det skal ha noe å si
                # UiO-edgecase: Forhåndskumulert og nederst på lista, skal bare ha en stemme. Er faktisk med, men skal bare ha en stemme.
                person_votes[ballot.chosen_list.id][candidate.id] += pre_cumulate_weight

    return person_votes, list_votes


def sainte_lagues_quotient(n):
    """Give quotient divider based on number of elected people"""
    return (2 * n) + 1


def modified_sainte_lagues_quotient(n):
    """Give quotient divider based on number of elected people"""
    if n == 0:
        return 1.4
    return (2 * n) + 1


def quotient_ratio(quotient_func, n):
    """Number needed to get directly from quotient n-1 to n"""
    return quotient_func(n - 1) / quotient_func(n)


def count(election_lists, list_votes, num_mandates, quotient_func):
    logger.info("Counting start")

    vote_number_lists = [
        (el_list, list_votes[el_list.id] * quotient_func(0))
        for el_list in election_lists
    ]
    vote_number_lists.sort(key=lambda x: x[1], reverse=True)

    mandates = {list.id: 0 for list in election_lists}

    for i in range(num_mandates):
        if (
            num_mandates - i < len(vote_number_lists)
            and vote_number_lists[0][1] == vote_number_lists[num_mandates - i][1]
        ):
            random_num = random.choice(range(num_mandates - i))
            election_list, vote_number = vote_number_lists.pop(random_num)
            logger.info("random draw") # Bør komme med noe her til protokoll
        else:
            election_list, vote_number = vote_number_lists.pop(0)

        mandates[election_list.id] += 1
        vote_number *= quotient_ratio(quotient_func, mandates[election_list.id])
        logger.info(f"mandate given to {election_list.id}")

        if mandates[election_list.id] < len(election_list.candidates):
            vote_number_lists.append((election_list, vote_number))
            if vote_number != 0:
                vote_number_lists.sort(key=lambda x: x[1], reverse=True)
        else:
            if vote_number_lists:
                logger.info(f"list {election_list.id} emptied")
                pass
            else:
                logger.info("all lists emptied")
                break

    logger.info("Counting done")
    return mandates


def sort_list(list_candidates, person_votes):
    """
    election_list = the candidates of the list getting sorted
    person_votes = this lists person_votes
    Sort first based on number of votes, then priority if equal
    Votes are made negative since python sorting goes from smallest to largest value
    """
    return sorted(list_candidates, key=lambda c: (-person_votes[c.id], c.priority))


def get_result(election):
    """
    result: {
        election_list: {
            num_candidates: int
            list_votes: int
            sorted_candidates_with_votes: [(candidate_id, votes)]
        }
    }
    """
    # TODO: Sjekk hvilket type listevalg, fikse riktig
    # TODO: hent ting fra counting_rules
    if election.type_str == "sainte_lague":

        person_votes, list_votes = get_list_counts(
            election.lists, election.ballots, election.num_choosable, 0.25
        )
        # TODO: person_votes bør ha med slengere/personstemmer
        mandates = count(
            election.lists,
            list_votes,
            election.num_choosable,
            sainte_lagues_quotient,
        )
        result = {}
        for el in election.lists:
            sorted_candidates = sort_list(el.candidates, person_votes[el.id])

            # TODO: statistikk på hvor stemmer kommer fra. altså slengere+personstemmer
            #       Kan kanskje løses fint med en enkel struct med kandidat+stemmer+slengere+personstemmer
            result[str(el.id)] = {
                "mandates": mandates[el.id],
                "list_votes": list_votes[el.id],
                "sorted_candidates_with_votes": [
                    (str(candidate.id), person_votes[el.id][candidate.id])
                    for candidate in sorted_candidates
                ],
            }
        return result
    # TODO: finn kandidatene som har fått plasser?, evt i egen funksjon


def get_protocol(election, result):
    meta = {
        'seats': election.meta["candidate_rules"]["seats"],
        'election_id': str(election.id),
        'election_name': election.name,
        'election_type': election.type_str,
        'candidate_ids': [str(cand.id) for cand in election.candidates],
        'candidates': {str(candidate.id): candidate.name for candidate in election.candidates},
        'list_ids': [str(el_list.id) for el_list in election.lists],
        'lists': {str(el_list.id): el_list.name for el_list in election.lists},
        'counted_at': datetime.datetime.now().astimezone(
            pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S'),
        'counted_by': None,
        'election_start': election.start.astimezone(
            pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S'),
        'election_end': election.end.astimezone(
            pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S'),
        # 'drawing': ?
        'ballots_count': election.total_amount_ballots,
        'counting_ballots_count': election.total_amount_counting_ballots,
        'empty_ballots_count': election.total_amount_empty_ballots,
        'result': result['list_result'],
    }
    protocol = Protocol(meta)
    print(protocol.render())
    return Protocol(meta)
