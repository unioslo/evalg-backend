import logging


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)
# TODO: logging sammen med protokoll? Kanskje en holder til en del


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

        for candidate in ballot.personal_votes_same:
            # Kan vurdere å sjekke at antall er ok her? Hvis det ikke fikses på forhånd (det er nok best å gjøre før)
            if candidate["cumulated"]:
                person_votes[ballot.chosen_list.id][candidate["id"]] += 2
            else:
                person_votes[ballot.chosen_list.id][candidate["id"]] += 1

        for other_candidate in ballot.personal_votes_other:
            list_votes[other_candidate["listId"]] += 1
            person_votes[other_candidate["listId"]][other_candidate["id"]] += 1

        for candidate in ballot.chosen_list.candidates:
            if candidate.pre_cumulated:
                # Gjør noe sjekk her på at personen ikke er strøket? Dersom det skal ha noe å si
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
    # Inn = Stemmer og info om lister
    # Ut = Antall kandidater (og vara?)
    #      ble det gjort tilfeldig trekning?
    # TODO: protokoll startinfo?

    vote_number_lists = [
        (el_list, list_votes[el_list.id] * quotient_func(0))
        for el_list in election_lists
    ]
    vote_number_lists.sort(key=lambda x: x[1])

    mandates = {list.id: 0 for list in election_lists}

    for i in range(num_mandates):
        if num_mandates - i < len(vote_number_lists):
            if vote_number_lists[-1 - num_mandates + i][1] == vote_number_lists[-1][1]:
                raise Exception("Random draw needed, but not yet implemented")
            # TODO: Protokoll_event, random draw

        election_list, vote_number = vote_number_lists.pop()
        mandates[election_list.id] += 1
        vote_number *= quotient_ratio(quotient_func, mandates[election_list.id])
        # TODO: Protokoll_event, mandate given to X list

        if mandates[election_list.id] < len(election_list.candidates):
            vote_number_lists.append((election_list, vote_number))
            vote_number_lists.sort(key=lambda x: x[1])
        else:
            # TODO: Protokoll_event, list emptied
            pass

    # TODO: Protokoll_event, sluttinfo
    # TODO: finne antall vara. Ofte ser det ut til å bare være samme som antall kandidater, evt pluss en konstant.
    #       Hvor skal dette legges inn? Får man det her eller under? Trenger kanskje ikke eget objekt for det, bare bruk "mandates"
    return mandates


def sort_list(list_candidates, person_votes):
    """
    election_list = the candidates of the list getting sorted
    person_votes = this lists person_votes
    Sort first based on number of votes, then priority if equal
    Votes are made negative since python sorting goes from smallest to largest value
    """
    return sorted(list_candidates, key=lambda c:(-person_votes[c.id], c.priority))


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
    if election.type_str == "party_list":
        person_votes, list_votes = get_list_counts(election.ballots, election, 4, 0.25)
        mandates = count(
            election.election_lists,
            list_votes,
            election.num_choosable,
            sainte_lagues_quotient,
        )
        result = {}
        for el in election.election_lists:
            sorted_candidates = sort_list(el.candidates, person_votes[el.id])

            # TODO: statistikk på hvor stemmer kommer fra. altså slengere+personstemmer
            #       Kan kanskje løses fint med en enkel struct med kandidat+stemmer+slengere+personstemmer
            result[el.id] = {
                "mandates": mandates[el.id],
                "list_votes": list_votes[el.id],
                "sorted_candidates_with_votes": [
                    (candidate.id, person_votes[el.id][candidate.id])
                    for candidate in sorted_candidates
                ]
            }
        return result
    # TODO: finn kandidatene som har fått plasser?, evt i egen funksjon
