# -*- coding: utf-8 -*-
"""Implementation of UiO's majority vote algorithm"""
import collections
import decimal
import logging

from evalg.counting import base, count


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class Result(base.Result):
    """UiOMV Result"""

    def __init__(self, meta, regular_candidates):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param regular_candidates: The elected regular candidates
        :type regular_candidates: collections.abc.Sequence
        """
        super().__init__(meta)
        self.regular_candidates = regular_candidates


class Protocol(base.Protocol):
    """UiOMV Protocol"""

    def __init__(self, meta, rounds):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param rounds: The list of rounds
        :type rounds: collections.abc.Sequence
        """
        super().__init__(meta)
        self.rounds = rounds

    def render(self, template='protocol_uiomv.tmpl'):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to be used (default: protocol_uiomv.tmpl)
        :type template: str

        :return: The rendered unicode text
        :rtype: str
        """
        return super().render(template=template)


class Round:
    """
    Round class.

    Represents a single counting round.
    """

    def __init__(self, counter, parent=None):
        """
        :param counter: Counter-object
        :type counter: Counter

        :param parent: The parent (recursive) object
        :type parent: Round
        """
        self._counter_obj = counter
        self._parent = parent
        self._round_id = 1 if self._parent is None else (
            self._parent.round_id + 1)
        # track the total amount of rounds
        self._round_cnt = (1 if self._parent is None else
                           (self._parent.round_cnt + 1))
        self._elected = []
        self._state = base.RoundState(self)
        self._counter_obj.append_state_to_current_path(self._state)

    @property
    def counter_obj(self):
        """counter_obj-property"""
        return self._counter_obj

    def count(self):
        """
        Performs the actual count.

        This method will either return a final state or call itself on a newly
        instanciated object. (recurse until final state is returned)

        :return: A state (result) for this count
        :rtype: RoundState
        """
        logger.info("Starting the MV count")
        ballot_weights = collections.Counter()  # ballot: weight - dict
        candidate_ballots = {}
        count_result_stats = {}
        results = collections.Counter()
        total_score = decimal.Decimal(0)
        elected_candidate = None

        # generate per pollbook stats
        for pollbook in self._counter_obj.election.pollbooks:
            count_result_stats[pollbook] = {}
            count_result_stats[pollbook]['total'] = decimal.Decimal(0)
            for candidate in self._counter_obj.candidates:
                candidate_ballots[candidate] = list()
                count_result_stats[pollbook][candidate] = {}
                count_result_stats[pollbook][candidate]['total'] = (
                    decimal.Decimal(0))
        for ballot in self._counter_obj.ballots:
            if not ballot.candidates:
                # blank ballot
                continue
            candidate_ballots[ballot.candidates[0]].append(ballot)
            ballot_weights[ballot] = ballot.pollbook.weight_per_pollbook
            total_score += ballot.pollbook.weight_per_pollbook
        for candidate, ballots in candidate_ballots.items():
            results[candidate] = decimal.Decimal(0)
            for ballot in ballots:
                results[candidate] += ballot_weights[ballot]
                count_result_stats[ballot.pollbook][
                    candidate]['total'] += ballot_weights[ballot]
                count_result_stats[ballot.pollbook][
                    'total'] += ballot_weights[ballot]
        # set % of total pollbook score - stats
        for pollbook in self._counter_obj.election.pollbooks:
            logger.info("Pollbook %s has a total score: %s",
                        pollbook.name,
                        count_result_stats[pollbook]['total'])
            for candidate in count_result_stats[pollbook]:
                if candidate == 'total':
                    continue
                if not count_result_stats[pollbook][candidate]['total']:
                    # avoid division by 0 and optimize...
                    # here the divisor can not be 0 if divident is not zero
                    count_result_stats[pollbook][candidate][
                        'percent_pollbook'] = decimal.Decimal(0)
                    logger.info(
                        "Candidate %s has a score of 0 in that pollbook",
                        candidate)
                    continue
                count_result_stats[pollbook][candidate]['percent_pollbook'] = (
                    (decimal.Decimal(100) *
                     count_result_stats[pollbook][candidate]['total']) /
                    count_result_stats[pollbook]['total']).quantize(
                        decimal.Decimal('1.00'),
                        decimal.ROUND_HALF_EVEN)
                logger.info(
                    "Candidate %s has a score of %s (%s%%) in that pollbook",
                    candidate,
                    count_result_stats[pollbook][candidate]['total'],
                    count_result_stats[pollbook][candidate][
                        'percent_pollbook'])
        count_results = results.most_common()
        logger.info("Total score: %s", total_score)
        logger.info("Half score: %s", total_score / decimal.Decimal(2))
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.NEW_COUNT,
                {'count_results': count_results,
                 'count_result_stats': count_result_stats,
                 'half_score': total_score / decimal.Decimal(2),
                 'total_score': total_score}))
        for vcount in count_results:
            # debugging mostly
            candidate, candidate_count = vcount
            if candidate_count > total_score / decimal.Decimal(2):
                logger.info("Candidate %s: %s (has more than 1/2 of the total "
                            "score and will be elected)",
                            candidate,
                            candidate_count)
                elected_candidate = candidate
                continue
            logger.info("Candidate %s: %s", candidate, candidate_count)
        if elected_candidate is None:
            # drawing
            logger.info(
                "None of the above candidates reached 1/2 of the total score. "
                "Drawing candidate to elect")
            elected_candidate = self._counter_obj.draw_candidate([
                count_results[0][0],
                count_results[1][0]])
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.DRAW_SELECT,
                {'candidate': str(elected_candidate.id)}))
        self._elected.append(elected_candidate)
        self._state.add_elected_candidate(elected_candidate)
        logger.info("Candidate %s is elected", elected_candidate)
        self._state.add_event(
            count.CountingEvent(count.CountingEventType.CANDIDATE_ELECTED,
                                {'candidate': str(elected_candidate.id)}))
        self._state.final = True
        return self._state
