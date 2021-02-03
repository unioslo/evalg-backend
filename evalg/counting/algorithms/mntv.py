# -*- coding: utf-8 -*-
"""Implementation of a Multiple non-transferable vote algorithm."""
import collections
import decimal
import logging
import traceback

from evalg.counting import base, count


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class RequiredCandidatesElected(Exception):
    """Raised when all required candidates within a group are elected"""


class Result(base.Result):
    """MV Result"""

    def __init__(self, meta, regular_candidates, substitute_candidates):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param regular_candidates: The elected regular candidates
        :type regular_candidates: collections.abc.Sequence
        """
        super().__init__(meta)
        self.regular_candidates = regular_candidates
        self.substitute_candidates = substitute_candidates


class Protocol(base.Protocol):
    """MNTV Protocol"""

    def __init__(self, meta, rounds):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param rounds: The list of rounds
        :type rounds: collections.abc.Sequence
        """
        super().__init__(meta)
        self.rounds = rounds

    def render(self, template='protocol_mntv.tmpl'):
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
        self._elected = []  # All elected candidates, (regular + substitutes)
        self._elected_substitutes = []
        self._state = base.RoundState(self)
        self._counter_obj.append_state_to_current_path(self._state)
        self._count_results = []

        self._quotas_disabled = not bool(self._counter_obj.quotas)
        self._update_quota_status()

    @property
    def counter_obj(self):
        """counter_obj-property"""
        return self._counter_obj

    def _can_elect_candidate(self, candidate, candidate_count, total_score, results):
        """
        Check if a candidate can be elected.

        To be elected, a candidate must have:
        - More then 1/(number of seats) of the total score
        - More votes then the next candidate.
        """

        if candidate_count > total_score / decimal.Decimal(
                self.counter_obj.election.num_choosable):
            # TODO: Check quotas..
            logger.info("Candidate %s: %s (has more than 1/%d of the total "
                        "score and will be elected)",
                        candidate,
                        candidate_count,
                        self.counter_obj.election.num_choosable)
            return True

        return False

    def _set_count_results(self, count_results):
        self._count_results = count_results

    def _get_remaining_candidates(self):
        x = [x for x in self._count_results if x[0] not in self._elected]
        return x

    def _get_next_candidates(self):
        remaining = self._get_remaining_candidates()
        _, cur_value = remaining[0]
        return [x for x in remaining if x[1] == cur_value]

    def _get_globally_unelected_candidates(self):
        """Returns all unelected candidates (globally)"""
        total = set(self._counter_obj.candidates)
        elected = set(self._elected)
        return tuple(total.difference(elected))

    def _get_unelected_quota_members(self, quota):
        """
        :return: Unelected members of `quota`
        :rtype: tuple
        """
        members = set(quota.members)
        return tuple(members.difference(set(self._elected)))

    def _elect_candidate(self, candidate, regular):
        """
         Elects a single candidate as a regular representative

         :param candidate: Candidate-object
         :type candidate: Candidate

         :param regular: True if we are electing a regular candidate
         :type regular: bool
         """
        # regulars
        if (regular and
                len(self._elected) >= self._counter_obj.election.num_choosable):
            raise RequiredCandidatesElected
        # substitutes
        if (not regular and
                len(self._elected) >= (
                self._counter_obj.election.num_choosable +
                self._counter_obj.election.num_substitutes)):
            raise RequiredCandidatesElected
        if candidate in self._elected:
            # should not happen
            logger.info("Candidate %s is already elected", candidate)
            return
        if self._quotas_disabled:
            self._elected.append(candidate)
            self._state.all_elected_candidates = self._elected
            if not regular:
                self._elected_substitutes.append(candidate)
                self._state.all_elected_substitutes = self._elected_substitutes
            logger.info("Candidate %s is elected", candidate)
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.CANDIDATE_ELECTED,
                {'candidate': str(candidate.id)}))
            return

        # quota rules have to be enforced
        if self._is_max_quota_full(candidate, regular):
            logger.info("Candidate %s is a member of a quota-group "
                        "that reached its max. value",
                        candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.MAX_QUOTA_VALUE_EXCLUDED,
                    {'candidate': str(candidate.id)}))
            return
        self._elected.append(candidate)
        self._state.all_elected_candidates = self._elected
        if not regular:
            self._elected_substitutes.append(candidate)
            self._state.all_elected_substitutes = self._elected_substitutes
        logger.info("Candidate %s is elected", candidate)
        self._state.add_event(count.CountingEvent(
            count.CountingEventType.CANDIDATE_ELECTED,
            {'candidate': str(candidate.id)}))
        return

    def _elect_regular(self):
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.NEW_REGULAR_ROUND, {}))
        for vcount in self._get_remaining_candidates():
            if len(self._elected) == self._counter_obj.candidates:
                logger.info("No more candidates left to elect")
                break
            candidate, _ = vcount
            try:
                self._elect_candidate(candidate, regular=True)
            except RequiredCandidatesElected:
                logger.info("All required regular candidates are elected")
                break
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TERMINATE_REGULAR_COUNT, {}))

    def _elect_substitutes(self):
        """Elects substitute representatives"""
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.NEW_SUBSTITUTE_ROUND, {}))
        for vcount in self._get_remaining_candidates():
            if len(self._elected_substitutes) == self._counter_obj.election.num_substitutes:
                logger.info("No more candidates left to elect")
                break
            candidate, _ = vcount
            try:
                self._elect_candidate(candidate, regular=False)
            except RequiredCandidatesElected:
                logger.info("All required substitute candidates have been elected")
                break

        # If there are less candidates then seats, we end up her as well.
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TERMINATE_SUBSTITUTE_COUNT, {}))

    def _draw_candidate_order(self, count_results):

        logger.info('At least two candidates have the same score. '
                    'Drawing lots')
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.SAME_SCORE, {}))

        unpacked_results = {}
        for vcount in count_results:
            candidate, candidate_count = vcount
            if candidate_count not in unpacked_results:
                unpacked_results[candidate_count] = [candidate]
            else:
                unpacked_results[candidate_count].append(candidate)

        count_results = []  # overwrite
        for count_result, candidates in unpacked_results.items():
            if len(candidates) > 1:
                self._counter_obj.shuffle_candidates(candidates)
            for candidate in candidates:
                count_results.append((candidate, count_result))

        return count_results

    def _perform_count(self, count_results, count_result_stats, pollbook):
        """
        Performs the logging / debugging part of the count

        :param count_results: The results of the count .most_common
        :type count_results: list

        :param count_result_stats: The result stats generated by the caller
        :type count_result_stats: dict
        """
        logger.info(count_results)
        for x in count_result_stats:
            logger.info(x)
        for vcount in count_results:
            candidate, candidate_count = vcount
            logger.info(candidate)
            logger.info("Candidate %s: %s -> %s",
                        candidate,
                        str(count_result_stats[pollbook][candidate].items()),
                        candidate_count)
        try:
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_COUNT,
                    {'count_results': count_results,
                     'count_result_stats': count_result_stats}))
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            raise e

    def _get_candidate_quota_groups(self, candidate):
        """
        :param : The Candidate-object
        :type : Candidate

        :return: The quota groups `candidate` is member of
        :rtype: tuple
        """
        return tuple(filter(lambda q: candidate in q.members,
                            self._counter_obj.quotas))

    def _is_max_quota_full(self, candidate, regular):

        """
        Checks if `candidate` is member of quota groups(s) that has reached
        its max. value

        :param candidate: The candidate to examine
        :type candidate: Candidate

        :param regular: True if we are electing a regular candidate
        :type regular: bool

        :return: True of candidate is member of at least one group with max
        :rtype: bool
        """
        if self._quotas_disabled:
            logger.debug("Quotas disabled")
            return False
        quota_groups = self._get_candidate_quota_groups(candidate)
        if not quota_groups:
            logger.debug("%s is not member of any quota-group(s)", candidate)
            return False
        for quota_group in quota_groups:
            members = set(quota_group.members)
            if regular:
                max_value = self._counter_obj.max_choosable(quota_group)
                sum_elected_members = len(
                    members.intersection(set(self._elected)))
            else:
                max_value = self._counter_obj.max_substitutes(quota_group)
                sum_elected_members = len(
                    members.intersection(set(self._elected_substitutes)))
            if sum_elected_members >= max_value:
                return True
        return False

    def _update_quota_status(self):
        """
        Updates the quota status for candidates.

        Re-checks and if necessary disables quota-checks.
        """
        # this method *MUST* be rewritten if more than gender-quota
        # should be handled
        if self._quotas_disabled:
            return None
        empty_quota_group = False
        no_min_value = False
        for quota_group in self._counter_obj.quotas:
            if not quota_group.members:
                empty_quota_group = True
            if not quota_group.min_value:
                no_min_value = True
        # this is for event (protocol) purposes only
        if empty_quota_group:
            logger.info("At least one quota group is empty. "
                        "Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_GROUP_EMPTY,
                {}))
            self._quotas_disabled = True
            return None
        if no_min_value:
            logger.info("At least one quota-group has min_value == 0. "
                        "Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_MIN_VALUE_ZERO,
                {}))
            self._quotas_disabled = True
            return None
        if (
                len(self._counter_obj.candidates) <=
                self._counter_obj.election.num_choosable
        ):
            logger.info("Candidates <= regular cendidates to "
                        "elect. Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_NOT_ENOUGH_CANDIDATES,
                {}))
            self._quotas_disabled = True
        return None

    def _update_quota_values(self):
        """
        Updates the quota values for substitute candidates.

        Re-checks and if necessary updates `min_value_substitutes` and
        `max_value_substitutes` for the defined quota-groups (if any).

        This method should only be called before the start of the
        substitute count.
        """
        # this method *MUST* be rewritten if more than gender-quota
        # should be handled
        if self._quotas_disabled:
            return None
        # adjust the min_value_substitutes for quotas, in case not enough
        # candidates
        quota_unelected = {}
        empty_quota_group = False
        for quota_group in self._counter_obj.quotas:
            quota_unelected[quota_group] = [
                str(cand.id) for
                cand in self._get_unelected_quota_members(quota_group)]
            unelected = len(quota_unelected[quota_group])
            if not unelected:
                # reevaluate this statement in the future if more than 2
                # groups can be used! (not only gender - quota)
                empty_quota_group = True
            if (
                    quota_group.min_value_substitutes and
                    unelected < quota_group.min_value_substitutes
            ):
                logger.info("Amount unelected members (%d) in "
                            "quota-group %s < than current "
                            "min_value_substitutes %d. Adjusting.",
                            unelected,
                            quota_group.name,
                            quota_group.min_value_substitutes)
                self._state.add_event(count.CountingEvent(
                    count.CountingEventType.QUOTA_MIN_VALUE_SUB_ADJUSTED, {
                        'quota_group_name': quota_group.name,
                        'current_value': quota_group.min_value_substitutes,
                        'new_value': unelected}))
                quota_group.min_value_substitutes = unelected
        # once min-values are correct, fetch the max-valuee and create an event
        # this is for event (protocol) purposes only
        no_min_value_substitutes = False
        quotas = []
        for quota_group, unelected_members in quota_unelected.items():
            if not quota_group.min_value_substitutes:
                no_min_value_substitutes = True
            max_val = self._counter_obj.max_substitutes(quota_group)
            logger.info("Quota-group %s: min_value_substitutes: %d, "
                        "max_value_substitutes: %d, %d unelected members",
                        quota_group.name,
                        quota_group.min_value_substitutes,
                        max_val,
                        len(unelected_members))
            quotas.append(
                {'name': quota_group.name,
                 'min_value_substitutes': quota_group.min_value_substitutes,
                 'max_value_substitutes': max_val,
                 'unelected_members': unelected_members})
        self._state.add_event(count.CountingEvent(
            count.CountingEventType.QUOTA_SUB_UPDATED,
            {'quotas': quotas}))
        if empty_quota_group:
            logger.info("At least one quota group is now empty. "
                        "Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_SUB_GROUP_EMPTY,
                {}))
            self._quotas_disabled = True
            return None
        if no_min_value_substitutes:
            logger.info("At least one quota-group has min_value_substitutes. "
                        "Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_SUB_MIN_VALUE_ZERO,
                {}))
            self._quotas_disabled = True
            return None
        if (
                len(self._get_globally_unelected_candidates()) <=
                self._counter_obj.election.num_substitutes
        ):
            logger.info("Unelected candidates <= substitute cendidates to "
                        "elect. Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_SUB_NOT_ENOUGH_CANDIDATES,
                {}))
            self._quotas_disabled = True
        return None

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
                count_result_stats[pollbook][candidate]['amount'] = 0
        for ballot in self._counter_obj.ballots:
            if not ballot.candidates:
                # blank ballot
                continue

            # Add all candidates from ballot
            # TODO add check for more then one vote for a candidate in the ballot.
            # TODO, add this check in the api
            for candidate in ballot.candidates:
                candidate_ballots[candidate].append(ballot)
                ballot_weights[ballot] = ballot.pollbook.weight_per_pollbook
                total_score += ballot.pollbook.weight_per_pollbook

        for candidate, ballots in candidate_ballots.items():
            results[candidate] = decimal.Decimal(0)
            for ballot in ballots:
                results[candidate] += ballot_weights[ballot]
                count_result_stats[ballot.pollbook][
                    candidate]['total'] += ballot_weights[ballot]
                count_result_stats[ballot.pollbook][candidate]['amount'] += 1
                count_result_stats[ballot.pollbook][
                    'total'] += ballot_weights[ballot]

        # Stats?
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

        # Sort the candidates by their vote score
        count_results = results.most_common()
        for pollbook in self._counter_obj.election.pollbooks:
            self._perform_count(count_results, count_result_stats, pollbook)

        if len(set([x[1] for x in results.most_common()])) < len(count_results):
            # There is at least two candidate with a equal score.
            # Drawing the order.
            count_results = self._draw_candidate_order(count_results)
            try:
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.NEW_COUNT,
                        {'count_results': count_results,
                         'count_result_stats': count_result_stats}))
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
                raise e

        self._set_count_results(count_results)

        # More stats?
        total_stats = {}
        for vcount in self._get_remaining_candidates():
            # debugging mostly
            candidate, candidate_count = vcount
            total_stats[str(candidate.id)] = {}
            if total_score:
                total_stats[str(candidate.id)]['percent_score'] = str(
                    (decimal.Decimal(100) * candidate_count /
                     total_score).quantize(
                        decimal.Decimal('1.00'), decimal.ROUND_HALF_EVEN))
            else:
                total_stats[str(candidate.id)]['percent_score'] = '0'
            logger.info("Candidate %s: %s", candidate, candidate_count)

        # We pop candidates from the top. By nr of votes.

        self._elect_regular()
        # reset self._quotas_disabled
        self._quotas_disabled = not bool(self._counter_obj.quotas)
        self._update_quota_values()
        self._elect_substitutes()

        logger.info("Total score: %s", total_score)
        logger.info("Half score: %s", total_score / decimal.Decimal(2))
        self._state.all_elected_candidates = self._elected
        self._state.final = True
        return self._state
