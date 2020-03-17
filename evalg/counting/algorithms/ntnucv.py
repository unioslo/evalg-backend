# -*- coding: utf-8 -*-
"""
Implementation of NTNU's cumulative voting algorithm used by USN

TODO: Events and protocol template to be created
"""
import collections
import decimal
import logging

from evalg.counting import base, count


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class RequiredCandidatesElected(Exception):
    """Raised when all required candidates within a group are elected"""


class Result(base.Result):
    """NTNUCV Result"""

    def __init__(self, meta, regular_candidates, substitute_candidates):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param regular_candidates: The elected regular candidates
        :type regular_candidates: collections.abc.Sequence

        :param substitute_candidates: The elected substitute candidates
        :type substitute_candidates: collections.abc.Sequence
        """
        super().__init__(meta)
        self.regular_candidates = regular_candidates
        self.substitute_candidates = substitute_candidates


class Protocol(base.Protocol):
    """NTNUCV Protocol"""

    def __init__(self, meta, rounds):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param rounds: The list of rounds
        :type rounds: collections.abc.Sequence
        """
        super().__init__(meta)
        self.rounds = rounds

    def render(self, template='protocol_ntnucv.tmpl'):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to use (default: protocol_ntnucv.tmpl)
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

    def __init__(self, counter):
        """
        :param counter: Counter-object
        :type counter: Counter
        """
        self._counter_obj = counter
        self._quotas_disabled = not bool(self._counter_obj.quotas)
        # track the total amount of rounds
        self._elected = []  # all elected candidates (regular + substitutes)
        self._elected_substitutes = []  # all elected substitutes
        self._state = base.RoundState(self)
        self._counter_obj.append_state_to_current_path(self._state)
        self._update_quota_status()

    @property
    def counter_obj(self):
        """counter_obj-property"""
        return self._counter_obj

    def __str__(self):
        return 'Round: 1'

    def count(self):
        """
        Performs the actual count.

        This method will either return a final state or call itself on a newly
        instanciated object. (recurse until final state is returned)

        :return: A state (result) for this count
        :rtype: RoundState
        """
        logger.info("Starting the NTNU-CV count")
        count_result_stats = {}
        results = collections.Counter()

        # set initial results
        divident = decimal.Decimal(1)
        factors = tuple([decimal.Decimal(f) for f in
                         range(1, len(self._counter_obj.candidates) * 2, 2)])
        for candidate in self._counter_obj.candidates:
            results[candidate] = decimal.Decimal(0)
            count_result_stats[candidate] = {int(f): 0 for f in factors}
        for ballot in self._counter_obj.ballots:
            if not ballot.candidates:
                # blank ballot
                continue
            for idx, candidate in enumerate(ballot.candidates):
                results[candidate] += divident / factors[idx]
                count_result_stats[candidate][int(factors[idx])] += 1
        count_results = results.most_common()
        self._perform_count(count_results, count_result_stats)
        # now see if two or more candidates have the same score
        scores = [r[1] for r in count_results]
        if len(set(scores)) < len(count_results):
            # at least one duplicate
            logger.info('At least two candidates have the same score. '
                        'Drawing lots')
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.SAME_SCORE, {}))
            unpacked_results = {}
            # this works only with Python >= 3.6
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
            # new event, debug...
            self._perform_count(count_results, count_result_stats)
        self._elect_regulars(count_results)
        # reset self._quotas_disabled
        self._quotas_disabled = not bool(self._counter_obj.quotas)
        self._update_quota_values()
        self._elect_substitutes(count_results)
        self._state.final = True
        return self._state

    def _elect_candidate(self, candidate, regular):
        """
        Elects a single candidate as a regular representative

        :param candidate: Candidate-object
        :type candidate: Candidate

        :param regular: True if we are electing a regular candidate
        :type regular: bool
        """
        # regulars
        if (
                regular and
                len(self._elected) >= self._counter_obj.election.num_choosable
        ):
            raise RequiredCandidatesElected
        # substitutes
        if (
                not regular and
                len(self._elected) >= (
                    self._counter_obj.election.num_choosable +
                    self._counter_obj.election.num_substitutes)
        ):
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

    def _elect_regulars(self, count_results):
        """
        Elects regular representatives from `count_results`

        :param count_results: The results of the count .most_common
        :type count_results: list
        """
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.NEW_REGULAR_ROUND, {}))
        for vcount in count_results:
            if len(self._elected) >= len(self._counter_obj.candidates):
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

    def _elect_substitutes(self, count_results):
        """
        Elects substitute representatives from `count_results`

        :param count_results: The results of the count .most_common
        :type count_results: list
        """
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.NEW_SUBSTITUTE_ROUND, {}))
        for vcount in count_results:
            if len(self._elected) >= len(self._counter_obj.candidates):
                logger.info("No more candidates left to elect")
                break
            candidate, _ = vcount
            try:
                self._elect_candidate(candidate, regular=False)
            except RequiredCandidatesElected:
                logger.info("All required substitute candidates are elected")
                break
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TERMINATE_SUBSTITUTE_COUNT, {}))

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

    def _perform_count(self, count_results, count_result_stats):
        """
        Performs the logging / debugging part of the count

        :param count_results: The results of the count .most_common
        :type count_results: list

        :param count_result_stats: The result stats generated by the caller
        :type count_result_stats: dict
        """
        for vcount in count_results:
            candidate, candidate_count = vcount
            logger.info("Candidate %s: %s -> %s",
                        candidate,
                        str(count_result_stats[candidate].items()),
                        candidate_count)
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.NEW_COUNT,
                {'count_results': count_results,
                 'count_result_stats_ntnu': count_result_stats}))

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
            # life is too short. we do not wait for other reasons.
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
        return None  # please pylint

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
                cand in
                tuple(set(quota_group.members).difference(set(self._elected)))]
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
        # now handle the special case of 1 regular and 1 substitute to elect.
        # this is handled differently here than in uiostv
        # USN election rules: §17.3 - B
        if (
                self._counter_obj.election.num_choosable == 1 and
                self._counter_obj.election.num_substitutes == 1 and
                len(self._elected) == 1  # paranoia
        ):
            regular_representative = self._elected[0]
            represented_group = self._get_candidate_quota_groups(
                regular_representative)[0]
            the_other_group = tuple(set(
                self._counter_obj.quotas).difference(
                    set((represented_group, ))))[0]
            if not quota_unelected[the_other_group]:
                empty_quota_group = True
            elif the_other_group.min_value_substitutes != 1:
                self._state.add_event(count.CountingEvent(
                    count.CountingEventType.QUOTA_MIN_VALUE_SUB_ADJUSTED,
                    {'quota_group_name': the_other_group.name,
                     'current_value': the_other_group.min_value_substitutes,
                     'new_value': 1}))
                the_other_group.min_value_substitutes = 1
            if represented_group.min_value_substitutes:
                self._state.add_event(count.CountingEvent(
                    count.CountingEventType.QUOTA_MIN_VALUE_SUB_ADJUSTED,
                    {'quota_group_name': represented_group.name,
                     'current_value': represented_group.min_value_substitutes,
                     'new_value': 0}))
                represented_group.min_value_substitutes = 0
        # once min-values are correct, fetch the max-values and create an event
        quotas = []
        unelected_candidates = 0
        for quota_group, unelected_members in quota_unelected.items():
            max_val = self._counter_obj.max_substitutes(quota_group)
            len_unelected_members = len(unelected_members)
            logger.info("Quota-group %s: min_value_substitutes: %d, "
                        "max_value_substitutes: %d, %d unelected members",
                        quota_group.name,
                        quota_group.min_value_substitutes,
                        max_val,
                        len_unelected_members)
            quotas.append(
                {'name': quota_group.name,
                 'min_value_substitutes': quota_group.min_value_substitutes,
                 'max_value_substitutes': max_val,
                 'unelected_members': unelected_members})
            unelected_candidates += len_unelected_members
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
        if (
                unelected_candidates <=
                self._counter_obj.election.num_substitutes
        ):
            logger.info("Unelected candidates <= substitute cendidates to "
                        "elect. Removing quota-rules.")
            self._state.add_event(count.CountingEvent(
                count.CountingEventType.QUOTA_SUB_NOT_ENOUGH_CANDIDATES,
                {}))
            self._quotas_disabled = True
        return None  # please pylint
