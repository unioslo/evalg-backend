# -*- coding: utf-8 -*-
"""Implementation of the UiO STV algorithm"""
import collections
import decimal
import logging
import math
import operator

from evalg.counting import base, count


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class NoMoreElectableCandidates(Exception):
    """Raised when §19.1 is detected"""
    pass


class NoMoreExcludableCandidates(Exception):
    """
    Raised in a substitute round when all excludable candidates
    are protected by $21
    """
    pass


class NoMoreGloballyElectableCandidates(Exception):
    """Raised when §19.1 is detected (globally)"""
    pass


class RequiredCandidatesElected(Exception):
    """Raised when §19.2 is detected"""
    pass


class SubstituteCandidateElected(Exception):
    """Raised when a single substitute candidate is elected"""
    pass


class Result(base.Result):
    """UiOSTV Result"""

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
    """UiOSTV Protocol"""

    def __init__(self, meta, rounds):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param rounds: The list of rounds
        :type rounds: collections.abc.Sequence
        """
        super().__init__(meta)
        self.rounds = rounds

    def render(self, template='protocol_uiostv.tmpl'):
        """
        Renders the protocol using jinja2 template `template`

        :param template: The template to be used
                         (default: protocol_uiostv.tmpl)
        :type template: str

        :return: The rendered unicode text
        :rtype: str
        """
        return super().render(template=template)


class RoundState(base.RoundState):
    """
    RoundState-class.

    Represents the state of the round after a the count is performed.

    This class should inherit from abstract RoundState that is agnostic to
    counting method(s).
    """

    def __init__(self, round_obj):
        """
        :param round_obj: The round-counting object
        :type round_obj: object
        """
        super().__init__(round_obj)
        self._substitute_final = False  # final for a particular substitute
        self._excluded = tuple()  # tuple of candidates excluded in this round
        self._all_elected_candidates = tuple()  # all elected candidates so far
        self._all_elected_substitutes = tuple()  # only the substitute cand.
        self._quota_excluded = tuple()  # tuple of quota-excluded candidates
        # ballots weight of all transfered ballots at the moment of transfer
        self._transferred_ballot_weights = collections.Counter()
        self._transferred_candidate_ballots = {}  # candidate: ballot-list dict
        self._paragraph_19_1 = False  # §19.1 in the corresponding round

    @property
    def all_elected_candidates(self):
        """all_elected_candidates-property"""
        return self._all_elected_candidates

    @all_elected_candidates.setter
    def all_elected_candidates(self, candidates):
        """all_elected_candidates-property setter"""
        self._all_elected_candidates = tuple(candidates)

    @property
    def all_elected_substitutes(self):
        """all_elected_substitutes-property"""
        return self._all_elected_substitutes

    @all_elected_substitutes.setter
    def all_elected_substitutes(self, candidates):
        """all_elected_substitutes-property setter"""
        self._all_elected_substitutes = tuple(candidates)

    @property
    def excluded(self):
        """excluded-property"""
        return self._excluded

    @property
    def paragraph_19_1(self):
        """paragraph_19_1-property"""
        return self._paragraph_19_1

    @paragraph_19_1.setter
    def paragraph_19_1(self, value):
        """paragraph_19_1-property setter"""
        self._paragraph_19_1 = value

    @property
    def quota_excluded(self):
        """quota_excluded-property"""
        return self._quota_excluded

    @property
    def substitute_final(self):
        """substitute_final-property"""
        return self._substitute_final

    @substitute_final.setter
    def substitute_final(self, value):
        """substitute_final-property setter"""
        self._substitute_final = value

    @property
    def transferred_ballot_weights(self):
        """transferred_ballot_weights-property"""
        return self._transferred_ballot_weights

    def __str__(self):
        return 'State for round: {round_obj}'.format(round_obj=self._round_obj)

    def add_excluded_candidate(self, candidate):
        """
        Sets self._excluded to a new tuple containing `candidate`

        :param candidate: Candidate object
        :type candidate: object
        """
        self._excluded = self._excluded + (candidate, )

    def add_quota_excluded_candidate(self, candidate):
        """
        Sets self._quota_excluded to a new tuple containing `candidate`

        :param candidate: Candidate object
        :type candidate: object
        """
        self._quota_excluded = self._quota_excluded + (candidate, )

    def get_transferred_candidate_ballots(self, candidate):
        """
        Returns a tuple of the ballots transfered to `candidate` at the round
        for this state.

        :return: List of ballot objects
        :rtype: list
        """
        return self._transferred_candidate_ballots.get(candidate, [])

    def update_transferred_ballot_weights(self, ballot_weights):
        """
        Updates transferred_ballot_weights with ballot_weights

        Since self._transferred_ballot_weights is a Counter,
        this method implements the usual dict.update behaviour.

        :param ballot_weights: Additional ballot-weights
        :type ballot_weights: collections.Counter
        """
        for ballot, weight in ballot_weights.items():
            self._transferred_ballot_weights[ballot] = weight

    def update_transferred_candidate_ballots(self, candidate_ballots):
        """
        Updates transferred_candidate_ballots with `candidate_ballots`.

        :param candidate_ballots: Additional candidate-ballots
        :type candidate_ballots: dict
        """
        self._transferred_candidate_ballots.update(candidate_ballots)


class RegularRound:
    """
    Regular round class.

    Represents a single counting round for a regular (not substitute) round.
    """

    def __init__(self, counter, parent=None):
        """
        :param counter: Counter-object
        :type counter: Counter

        :param parent: The parent (recursive) object
        :type parent: RegularRound
        """
        self._counter_obj = counter
        self._parent = parent
        self._round_id = 1 if self._parent is None else (
            self._parent.round_id + 1)
        # track the total amount of rounds
        self._round_cnt = (1 if self._parent is None else
                           (self._parent.round_cnt + 1))
        # prevent infinite loops due to bugs
        if self._round_cnt > 500:
            logger.critical('Infinite recursion caught. Killing everything...')
            raise count.CountingFailure(
                'Infinite recursion caught in regular round')
        self._elected = []
        self._potentially_elected = []
        self._excluded = []
        # candidate: ballots-list - dict
        self._transferred_uncounted_ballots = {}
        # the vote count of the remaining candidates
        self._vcount_results_remaining = collections.Counter()
        self._surplus_per_elected_candidate = collections.Counter()
        self._state = RoundState(self)  # we store the state of the round
        self._counter_obj.append_state_to_current_path(self._state)
        if self._parent is None:
            # first round
            # make it possible to "manually" disable quotas for this particular
            # ElectionPath
            self._quotas_disabled = not bool(self._counter_obj.quotas)
            self._update_quota_status()  # before the new round
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_REGULAR_ROUND,
                    {'round_id': self._round_id,
                     'election_number': '',
                     'elected_count': 0,
                     'sum_surplus': '0',
                     'remaining_to_elect_count': min(
                         [self._counter_obj.election.num_choosable,
                          len(self._counter_obj.candidates)]),
                     'candidates_to_elect_count': min(
                         [self._counter_obj.election.num_choosable,
                          len(self._counter_obj.candidates)]),
                     'round_count': self._round_cnt}))
            self._election_number = self._get_election_number()
            self._set_initial_ballot_state()
        else:
            self._quotas_disabled = self._parent.quotas_disabled
            self._election_number = self._parent.election_number
            self._elected = list(self._parent.elected)
            self._excluded = list(self._parent.excluded)
            self._vcount_results_remaining = collections.Counter(
                self._parent.vcount_results_remaining)
            self._surplus_per_elected_candidate = collections.Counter(
                self._parent.surplus_per_elected_candidate)
            self._ballot_weights = collections.Counter(
                self._parent.ballot_weights)
            self._candidate_ballots = dict(self._parent.candidate_ballots)
            self._ballot_owners = dict(self._parent.ballot_owners)
            self._transferred_uncounted_ballots = dict(
                self._parent.transferred_uncounted_ballots)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_REGULAR_ROUND,
                    {'round_id': self._round_id,
                     'election_number': str(self._election_number),
                     'elected_count': len(self._elected),
                     'sum_surplus': str(self._get_total_surplus()),
                     'remaining_to_elect_count': min(
                         [self._counter_obj.election.num_choosable,
                          len(self._counter_obj.candidates)]) - len(
                              self._elected),
                     'candidates_to_elect_count': min(
                         [self._counter_obj.election.num_choosable,
                          len(self._counter_obj.candidates)]),
                     'round_count': self._round_cnt}))

    @property
    def ballot_owners(self):
        """ballot_owners-property"""
        return self._ballot_owners

    @property
    def ballot_weights(self):
        """ballot_weights-property"""
        return self._ballot_weights

    @property
    def candidate_ballots(self):
        """candidate_ballots-property"""
        return self._candidate_ballots

    @property
    def counter_obj(self):
        """counter_obj-property"""
        return self._counter_obj

    @property
    def elected(self):
        """elected-property"""
        return self._elected

    @property
    def election_number(self):
        """election_number-property"""
        return self._election_number

    @property
    def excluded(self):
        """excluded-property"""
        return self._excluded

    @property
    def has_remaining_surplus(self):
        """has_remaining_surplus-property"""
        # paranoia: >0 should not be necessary (but <0 also evaluates to True)
        return bool(
            self._surplus_per_elected_candidate and
            self._surplus_per_elected_candidate.most_common(1)[0][1] > 0)

    @property
    def parent(self):
        """parent-property"""
        return self._parent

    @property
    def quotas_disabled(self):
        """quotas_disabled-property"""
        return self._quotas_disabled

    @property
    def round_cnt(self):
        """elected-property"""
        return self._round_cnt

    @property
    def round_id(self):
        """id-property"""
        return self._round_id

    @property
    def state(self):
        """state-property"""
        return self._state

    @property
    def surplus_per_elected_candidate(self):
        """surplus_per_elected_candidate-property"""
        return self._surplus_per_elected_candidate

    @property
    def transferred_uncounted_ballots(self):
        """transferred_uncounted_ballots-property"""
        return self._transferred_uncounted_ballots

    @property
    def vcount_results_remaining(self):
        """vcount_results_remaining-property"""
        return self._vcount_results_remaining

    def __str__(self):
        return 'RegularRound: {id}/{total_count}'.format(
            id=self._round_id,
            total_count=self._round_cnt)

    def count(self):
        """
        Performs the actual count.

        This method will either return a final state or call itself on a newly
        instanciated object. (recurse until final state is returned)

        :return: A state (result) for this count
        :rtype: RoundState
        """
        logger.debug("---")
        if self._parent is None:
            logger.info("Starting regular count")
        logger.info("Counting round: %d (%d)",
                    self._round_id,
                    self._round_cnt)
        logger.info("Election number: %s",
                    self._election_number)
        # §19 - start by checking termination criteria
        logger.debug("Checking §19")
        if (
                self._parent is None and
                self._counter_obj.election.num_choosable <= 0
        ):
            logger.info(
                "No regular candidates to be elected. Terminating count.")
            return self._terminate_regular_count()
        try:
            self._check_remaining_candidates()  # §19.1
            self._check_election_quota_reached()  # §19.2
            logger.debug("Checking §19 - done")
            if self._parent is None:
                logger.debug("First round. No surplus here.")
                self._initiate_new_count()
                new_round = RegularRound(self._counter_obj, self)
                return new_round.count()
            # Checking if someone should be eliminated because of
            # max. value quota reached in previous round (§29). This is
            # done even before calculating the surplus.
            excludable_candidates = self._get_quota_excludable_candidates()
            for excludable_candidate in excludable_candidates:
                logger.info("Excluding: %s (§29)", excludable_candidate)
                # check §27 is case the candidate is member of several quotas
                if self._min_quota_required(excludable_candidate):
                    logger.info(
                        "Candidate %s must be elected in order to fulfill the "
                        "quota-rules. Skipping elimination.",
                        excludable_candidate)
                    continue
                self._state.add_quota_excluded_candidate(excludable_candidate)
                self._exclude_candidate(excludable_candidate)
            if excludable_candidates:
                # check §19.1 again
                self._check_remaining_candidates()
                self._transfer_ballots_from_excluded_candidates()
                self._initiate_new_count()
            # calculate surplus
            total_surplus = self._get_total_surplus()
            logger.info("Total surplus from %d elected candidate(s) "
                        "from previous round(s): %s",
                        len(self._surplus_per_elected_candidate),
                        total_surplus)
            # §16.3 - check if someone can be excluded
            excludable_candidates = self._get_excludable_candidates()
            if not excludable_candidates:
                logger.debug("No candidates for exclusion")
                self._state.add_event(count.CountingEvent(
                    count.CountingEventType.UNABLE_TO_EXCLUDE, {}))
                # §16.4 - check if there is any remaining surplus
                if self.has_remaining_surplus:
                    # §16.4 - A
                    surplus_items = self._get_greatest_surplus()
                    if len(surplus_items) > 1:
                        logger.info("%d candidates have the same and greatest "
                                    "surplus of %s",
                                    len(surplus_items),
                                    surplus_items[0][1])
                        surplus_candidates = []
                        for surplus_item in surplus_items:
                            surplus_candidates.append(surplus_item[0])
                            logger.info("Candidate %s", surplus_item[0])
                        logger.info("Drawing candidate whos surplus to "
                                    "transfer in accordance with §16.4 - A")
                        self._state.add_event(count.CountingEvent(
                            count.CountingEventType.SAME_SURPLUS,
                            {'candidates': [str(cand.id) for cand in
                                            surplus_candidates],
                             'identical_surplus': str(
                                 surplus_items[0][1])}))
                        drawn_candidate = self._counter_obj.draw_candidate(
                            surplus_candidates)
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.DRAW_SELECT,
                                {'candidate': str(drawn_candidate.id)}))
                        logger.info("Transferring the surplus of candidate %s",
                                    drawn_candidate)
                        self._transfer_surplus(drawn_candidate)
                        self._clear_candidate_surplus(drawn_candidate)
                    else:
                        surplus_candidate = surplus_items[0][0]
                        self._transfer_surplus(surplus_candidate)
                        self._clear_candidate_surplus(surplus_candidate)
                else:
                    logger.info(
                        "No available surplus. "
                        "Excluding candidates at the bottom (§16.4-B)")
                    bottom_candidates = self._get_filtered_excludables(
                        self._get_bottom_candidates())
                    if not bottom_candidates:
                        # all bottom candidates are "quota-protected"
                        logger.warning("No bottom candidates to exclude. "
                                       "Starting a new round")
                        cresults = self._vcount_results_remaining.most_common()
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.DISPLAY_STATUS,
                                {'count_results': cresults}))
                        new_round = RegularRound(self._counter_obj,
                                                 self)
                        return new_round.count()
                    if len(bottom_candidates) == 1:
                        # great! only one bottom candidate not protected
                        # by quota-rule
                        logger.info("Excluding: %s", bottom_candidates[0])
                        self._exclude_candidate(bottom_candidates[0])
                        self._check_remaining_candidates()
                    else:  # > 1 bottom_candidates to exclude
                        logger.info("%d bottom candidates to exclude.",
                                    len(bottom_candidates))
                        for bottom_candidate in bottom_candidates:
                            logger.info(
                                "Candidate %s: %s",
                                bottom_candidate,
                                self._vcount_results_remaining[
                                    bottom_candidate])
                        logger.info("Drawing candidate to exclude in "
                                    "accordance with §16.4 - B.")
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.BOTTOM_SCORE,
                                {'candidates': [str(cand.id) for cand in
                                                bottom_candidates],
                                 'identical_score': str(
                                     self._vcount_results_remaining[
                                         bottom_candidates[0]])}))
                        drawn_candidate = self._counter_obj.draw_candidate(
                            bottom_candidates)
                        logger.info("Candidate %s was drawn for exclusion.",
                                    drawn_candidate)
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.DRAW_SELECT,
                                {'candidate': str(drawn_candidate.id)}))
                        self._exclude_candidate(drawn_candidate)
                        self._check_remaining_candidates()
            for excludable_candidate in excludable_candidates:
                logger.info("Excluding: %s", excludable_candidate)
                self._exclude_candidate(excludable_candidate)
            # check §19.1 again
            self._check_remaining_candidates()
            self._transfer_ballots_from_excluded_candidates()
            if not excludable_candidates:
                self._initiate_new_count()
            new_round = RegularRound(self._counter_obj, self)
            return new_round.count()
        except NoMoreElectableCandidates:
            # §19.1
            logger.info("§19.1 Remaining candidates <= electable candidates")
            self._state.paragraph_19_1 = True
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TERMINATE_19_1, {}))
            try:
                self._elect_all_remaining_candidates()
            except RequiredCandidatesElected:
                # unless programming error, this is guaranteed
                logger.info("All required candidates are elected. "
                            "Terminating count according to §19.2.")
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.TERMINATE_19_2, {}))
            else:
                logger.error("Inconsistent relation between §19.1 and §19.2.")
            return self._terminate_regular_count()
        except RequiredCandidatesElected:
            # §19.2
            logger.info("All required candidates are elected. "
                        "Terminating count according to §19.2.")
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TERMINATE_19_2, {}))
            return self._terminate_regular_count()

    def get_candidate_election_state(self, candidate):
        """
        Returns the state where `candidate` was elected and 'None'
        if the candidate is not elected.

        :param candidate: The candidate-object
        :type candidate: object

        :return: The round-state or None
        :rtype: RoundState, None
        """
        if candidate in self._state.elected:
            return self._state
        if not self._parent:
            # this is the first round
            return None
        return self._parent.get_candidate_election_state(candidate)

    def _can_be_elected_together(self, candidates, elected=None):
        """
        Return True if all `candidates` can be elected together
        according to §29.
        """
        if elected is None:
            elected = self._elected
        pretend_elected = list(candidates) + elected
        for candidate in candidates:
            if self._max_quota_full(candidate, pretend_elected):
                return False
        return True

    def _check_election_quota_reached(self):
        """§19.2"""
        minimum_group = min([self._counter_obj.election.num_choosable,
                             len(self._counter_obj.candidates)])
        if len(self._elected) == minimum_group:
            raise RequiredCandidatesElected
        return False

    def _check_remaining_candidates(self):
        """§19.1"""
        if (
                len(self._get_remaining_candidates()) <=
                self._get_amount_remaining_to_be_elected()
        ):
            raise NoMoreElectableCandidates
        return True

    def _clear_candidate_surplus(self, candidate):
        """Clears (pop) the surplus of a candidate"""
        return self._surplus_per_elected_candidate.pop(candidate, None)

    def _elect_all_remaining_candidates(self):
        for rcandidate in self._get_remaining_candidates():
            logger.info("Candidate %s is elected according to §19.1",
                        rcandidate)
            self._state.add_event(
                count.CountingEvent(count.CountingEventType.ELECT_19_1,
                                    {'candidate': str(rcandidate.id)}))
            self._elect_candidate(rcandidate)

    def _elect_candidate(self, candidate):
        """Wraps the functionality of electing a candidate"""
        if candidate in self._state.quota_excluded:
            logger.info("Candidate %s is excluded based on quota. "
                        "Unable to elect",
                        candidate)
            return
        if candidate in self._excluded:
            logger.error("Candidate %s is marked as excluded. Unable to elect",
                         candidate)
            return
        self._elected.append(candidate)
        if candidate in self._potentially_elected:
            self._potentially_elected.pop(
                self._potentially_elected.index(candidate))
        logger.info("Candidate %s is elected", candidate)
        if not self._state.paragraph_19_1:
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.CANDIDATE_ELECTED,
                    {'candidate': str(candidate.id)}))
            self._update_surplus_for_elected_candidate(candidate)
        else:
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.CANDIDATE_ELECTED_19_1,
                    {'candidate': str(candidate.id)}))
        if self._vcount_results_remaining.pop(candidate, None) is None:
            logger.warning(
                "Candidate %s not found in vcount_results_remaining",
                candidate)
        self._state.add_elected_candidate(candidate)  # update the round-state
        self._state.all_elected_candidates = self._elected
        self._check_election_quota_reached()
        full_quota_groups = self._max_quota_full(candidate)
        excludable_candidates = []
        for full_quota_group in full_quota_groups:
            unelected_members = self._get_unelected_quota_members(
                full_quota_group)
            msg = 'Max-value for quota group {quota} is reached'.format(
                quota=full_quota_group.name)
            if not unelected_members:
                logger.debug(msg + ', but no unelected members. Continuing...')
            logger.debug(msg)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.MAX_QUOTA_VALUE_REACHED,
                    {'quota_group': full_quota_group.name,
                     'members': ([str(member.id) for
                                  member in unelected_members])}))
            excludable_candidates.extend(unelected_members)
        excludable_candidates = self._get_filtered_excludables(
            excludable_candidates)
        for excludable_candidate in excludable_candidates:
            logger.info("Candidate %s is member of a group that reached its "
                        "max. value. Excluding.",
                        excludable_candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.MAX_QUOTA_VALUE_EXCLUDED,
                    {'candidate': str(excludable_candidate.id)}))
            self._state.add_quota_excluded_candidate(excludable_candidate)
            self._exclude_candidate(excludable_candidate)
        if excludable_candidates:
            self._transfer_ballots_from_excluded_candidates()

    def _exclude_candidate(self, candidate):
        """Wraps the functionality of excluding a candidate"""
        # check for quota conditions: §27, §28
        if self._min_quota_required(candidate):
            # this is usually checked before calling this method, but
            # extra safety doesn't harm.
            logger.warning(
                "Candidate %s must be elected in order to fulfill the "
                "quota-rules. Skipping exclusion.",
                candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.CANDIDATE_QUOTA_PROTECTED,
                    {'candidate': str(candidate.id)}))
            return None
        if candidate in self._excluded:
            # in case of quota max. value reached exclusion
            logger.info("Candidate %s is already excluded", candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.EXCLUDED_EARLIER,
                    {'candidate': str(candidate.id)}))
            return None  # make pylint happy
        self._excluded.append(candidate)
        if self._vcount_results_remaining.pop(candidate, None) is None:
            logger.warning(
                "Candidate %s not found in vcount_results_remaining",
                candidate)
        self._state.add_excluded_candidate(candidate)  # update the round-state
        logger.info("Candidate %s is excluded", candidate)
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.CANDIDATE_EXCLUDED,
                {'candidate': str(candidate.id)}))
        self._check_remaining_candidates()
        return None  # please pylint

    def _get_bottom_candidates(self):
        """
        Return the candidates with lowest vcount from the last count.

        Used for implementing §16.4 - B, C

        :return: The candidates with lowest vcount from the last count
        :rtype: tuple
        """
        ordered_results = self._vcount_results_remaining.most_common()
        ordered_results.reverse()
        # some paranoia checks:
        if not ordered_results:
            logger.warning("No vcount entries left")
            return tuple()
        if len(ordered_results) < 2:
            logger.warning("< 2 vcount entries. Breaking §16.4-C assumptions")
            return tuple([ordered_results[0][0]])
        bottom_candidates = []
        min_vcount = ordered_results[0][1]
        for result in ordered_results:
            candidate, vcount = result
            if vcount == min_vcount:
                bottom_candidates.append(candidate)
            elif vcount > min_vcount:
                break
        if len(bottom_candidates) < 2:
            logger.warning("< 2 vcount bottom-entries. "
                           "Breaking §16.4-C assumptions")
        return tuple(bottom_candidates)

    def _get_election_number(self):
        """
        Calculates the election-number for this round according to §20

        :return: The election number calculated for this round
        :rtype: decimal.Decimal
        """
        # §13
        # Robert Hamer:
        # §13 We can use a smaller epsilon than 0.01.
        # Proposition:
        #  * prec >= 2
        #  * prec is at least 2 * math.log(counting-ballots, 10)
        counting_ballot_pollbook = (
            [ballot.pollbook.weight_per_pollbook for
             ballot in self._counter_obj.counting_ballots])
        if len(counting_ballot_pollbook) < 10:
            # avoid log(0) and large epsilon when 1 <= ballots < 10
            prec = 2
        else:
            prec = 2 * int(math.log(len(counting_ballot_pollbook), 10))
        # the quotient should not have a greater precision than epsilon
        quotient_precision = decimal.Decimal(10) ** -prec  # §18.3, §33
        epsilon = decimal.Decimal((0, (1, ), -prec))
        weight_counting_ballots = decimal.Decimal(
            sum(counting_ballot_pollbook))
        quotient = (
            weight_counting_ballots /
            decimal.Decimal(self._counter_obj.election.num_choosable + 1)
        ).quantize(
            quotient_precision,
            decimal.ROUND_DOWN)
        initial_e_number = quotient + epsilon
        logger.info("Calculating initial election number:")
        logger.info("Quotient (§18.3, §33): "
                    "(%s (weight of counting ballots) / (%s to elect + 1) "
                    "(with %d decimal precision) = %s",
                    weight_counting_ballots,
                    self._counter_obj.election.num_choosable,
                    prec,
                    quotient)
        logger.info("%s (quotient) + %s (epsilon) = %s",
                    quotient,
                    epsilon,
                    initial_e_number)
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.ELECTION_NUMBER,
                {'weight_counting_ballots': str(weight_counting_ballots),
                 'candidates_to_elect': (
                     self._counter_obj.election.num_choosable),
                 'substitute_number': 0,  # not a substitute round
                 'precision': str(prec),
                 'quotient': str(quotient),
                 'epsilon': str(epsilon),
                 'election_number': str(initial_e_number)}))
        return initial_e_number

    def _get_excludable_candidates(self):
        """
        Important implementation of §16.3

        :return: Candidates that can be excluded based on a previous count
        :rtype: tuple
        """
        if not self._parent or not self._vcount_results_remaining:
            # first round or no counts in the previous round
            return tuple()
        results = self._vcount_results_remaining.most_common()
        if len(results) < 2:
            # paranoia: this should not happen because of §19
            # that is always checked before exclusion
            return tuple()
        total_surplus = self._get_total_surplus()

        # §16.3 - D dictates that §16.3 - B is checked first and then §16.3 - A
        def sum_from(i):
            return sum(map(operator.itemgetter(1), results[i:]))

        largest_exclusion_group_size = 0
        for index, count_result in enumerate(results[:-1]):  # not the last one
            if sum_from(index + 1) + total_surplus < count_result[1]:
                largest_exclusion_group_size = len(results) - (index + 1)
                break
        else:
            # §16.3 - D
            return tuple()
        logger.info("§16.3 - D: Maximum to be excluded: %d",
                    largest_exclusion_group_size)
        # now check §16.3 - C
        max_possible_to_exclude = (
            len(self._get_remaining_candidates()) -
            self._get_amount_remaining_to_be_elected())
        remaining_candidates_after_exclusion = (
            len(self._get_remaining_candidates()) -
            largest_exclusion_group_size)
        logger.info("§16.3 - C: Remaining candidates after exclusion: %d",
                    remaining_candidates_after_exclusion)
        if largest_exclusion_group_size <= max_possible_to_exclude:
            # return the largest possible group
            return self._get_filtered_excludables(
                map(operator.itemgetter(0),
                    results[-largest_exclusion_group_size:]))
        # the candidates from exclusion are too many

        # pick a smaller size and perform the §16.3 - A check again!
        # Start with max_possible_to_exclude and if the test fails,
        # decrement the size by 1 and do it again
        # no candidates can be excluded if the size becomes 0
        while max_possible_to_exclude:
            if (
                    sum_from(-max_possible_to_exclude) + total_surplus <
                    results[-(max_possible_to_exclude + 1)][1]
            ):
                return self._get_filtered_excludables(
                    map(operator.itemgetter(0),
                        results[-max_possible_to_exclude:]))
            max_possible_to_exclude -= 1
        # §16.3 - A didn't pass for any subgroup (size)
        # Nobody can be excluded here and now
        return tuple()

    def _get_filtered_excludables(self, excludables):
        """
        Implements §27, §28

        :return: The excludables that actually can be excluded
        :rtype: tuple
        """
        filtered_excludables = []
        for excludable in excludables:
            # check for quota conditions: §27, §28
            if self._min_quota_required(excludable):
                logger.info(
                    "Candidate %s must be elected in order to fulfill the "
                    "quota-rules. Skipping exclusion.",
                    excludable)
                continue
            filtered_excludables.append(excludable)
        return tuple(filtered_excludables)

    def _get_greatest_surplus(self):
        """
        Implementation of §16.4 - A

        :return: Largest remaining surplus, None if no available surplus,
                 tuple of candidates with equal surpluses in accordance
                 with §16.4 - A
        :rtype: decimal.Decimal, None or tuple
        """
        if not self.has_remaining_surplus:
            return None
        ordered_surplus = (
            self._surplus_per_elected_candidate.most_common())
        if len(ordered_surplus) == 1:
            return tuple(ordered_surplus)
        # >= 2
        if ordered_surplus[0][1] > ordered_surplus[1][1]:
            # 1.candidate vcount > 2.candidate vcount == no relevant duplicates
            return tuple([ordered_surplus[0]])
        # at least 1 duplicate ... return the tuples with the highest vcount
        highest_vcount = ordered_surplus[0][1]
        duplicates = []
        for item in ordered_surplus:
            if item[1] >= highest_vcount:
                duplicates.append(item)
                continue
            break
        return tuple(duplicates)

    def _get_amount_remaining_to_be_elected(self):
        """
        Amount of candidates to be elected

        :return: Amount of candidates to be elected
        :rtype: int
        """
        return self._counter_obj.election.num_choosable - len(self._elected)

    def _get_candidate_quota_groups(self, candidate):
        """
        :return: The quota groups `candidate` is member of
        :rtype: tuple
        """
        return tuple(filter(lambda q: candidate in q.members,
                            self._counter_obj.quotas))

    def _get_candidate_transferrable_ballots(self,
                                             candidate,
                                             from_election_state):
        """
        This is the implementation of: §17.2 (no sorting) and §18.2

        :param candidate: The candidate object
        :type candidate: object

        :param from_election_state: Use the ballots from the election state?
        :type from_election_state: bool

        :return: Two element tuple:
                 - tuple of all transferrable ballots,
                 - tuple of all transferrable excluding those not containing
                   remaining candidates
        :rtype: tuple
        """
        if from_election_state:
            # used in §18.2
            election_state = self.get_candidate_election_state(candidate)
            if election_state is None:
                raise count.CountingFailure(
                    'Trying to transfer surplus from unelected candidate')
            ballots = election_state.get_transferred_candidate_ballots(
                candidate)
        else:
            ballots = self._candidate_ballots[candidate]
        # exclude ballots that do not contain any remaining candidate
        remaining_candidates = self._get_remaining_candidates()

        def contains_remaining_candidate(ballot):
            # use of sets is possible, but not faster
            for cand in ballot.candidates:
                if cand is candidate:
                    continue
                if cand in remaining_candidates:
                    return True
            return False

        return (tuple(ballots),
                tuple(filter(contains_remaining_candidate, ballots)))

    def _get_candidates_with_duplicate_scores(self, candidate, candidates):
        """
        Returns the candidates among `candidates` that have a similar score as
        `candidate`

        :return: Candidates with the same score (not counting `candidate`)
        :rtype: tuple
        """
        duplicates = []
        score = self._vcount_results_remaining[candidate]
        for can in candidates:
            if can is candidate:
                continue
            if can not in self._vcount_results_remaining:
                # already elected
                continue
            if self._vcount_results_remaining[can] == score:
                duplicates.append(can)
        return tuple(duplicates)

    def _get_new_owners(self, ballots):
        """
        Retuns a new ballot: owner dict for all ballots containing
        remainig candidates

        :return: The new ballot: owner dict
        :rtype: dict
        """
        new_owners = {}
        remaining_candidates = self._get_remaining_candidates()
        for ballot in ballots:
            current_owner = self._ballot_owners[ballot]
            for candidate in ballot.candidates:
                if candidate is current_owner:
                    # do not tranfer to yourself (in a substitute round)
                    continue
                if candidate in remaining_candidates:
                    new_owners[ballot] = candidate
                    break
        return new_owners

    def _get_quota_excludable_candidates(self):
        """
        Returns the excludable remaining candidates according to §26

        :return: The quota-excludable remaining candidates
        :rtype: tuple
        """
        if self._quotas_disabled:
            # no quota-rules defined
            return tuple()
        excludable_candidates = set()
        elected = set(self._elected)
        excluded = set(self._excluded)
        for quota_group in self._counter_obj.quotas:
            members = set(quota_group.members)
            max_value = self._counter_obj.max_choosable(quota_group)
            sum_elected_members = len(members.intersection(elected))
            if sum_elected_members >= max_value:
                excludable_candidates.update(
                    members.difference(elected.union(excluded)))
        return tuple(excludable_candidates)

    def _get_remaining_candidates(self):
        """
        A tuple of remaining candidates

        :return: The remaining candidates
        :rtype: tuple
        """
        total = set(self._counter_obj.candidates)
        elected = set(self._elected)
        excluded = set(self._excluded)
        return tuple(total.difference(elected.union(excluded)))

    def _get_total_surplus(self):
        """
        Returns the total surplus based on previous round(s)
        and corresponding states.

        :return: Remaining sureplus
        :rtype: decimal.Decimal
        """
        if not self._parent:
            return decimal.Decimal(0)
        return decimal.Decimal(
            sum(self._surplus_per_elected_candidate.values()))

    def _get_transferred_ballot_weights(self, candidate):
        """
        Returns the transferred_ballot_weights for the state the candidate
        was elected in.
        """
        election_state = self.get_candidate_election_state(candidate)
        if election_state is None:
            raise count.CountingFailure(
                'Trying to transfer surplus from unelected candidate')
        return election_state.transferred_ballot_weights

    def _get_vcount_per_candidate(self):
        """
        Returns the candidate: vcount overview based on the *current state*.

        That means that the current state should be modified before this
        count can take place.

        :return: {candidate: votes} Counter
        :rtype: collections.Counter
        """
        vcount = collections.Counter()
        candidate_ballots = self._transferred_uncounted_ballots
        ballot_weights = self._state.transferred_ballot_weights
        if not self._vcount_results_remaining:
            # first count.
            for candidate, ballots in candidate_ballots.items():
                vcount[candidate] = (
                    sum(map(lambda b: ballot_weights[b], ballots)))
            self._transferred_uncounted_ballots.clear()
            return vcount

        # not the first count. A previous count exists
        for candidate, ccount in self._vcount_results_remaining.items():
            # new vote count = old vcount + count for transferred ballots
            if candidate in candidate_ballots:  # received some ballots
                vcount[candidate] = (
                    ccount +
                    sum(map(lambda b: ballot_weights[b],
                            candidate_ballots[candidate])))
            else:
                vcount[candidate] = ccount
        self._transferred_uncounted_ballots.clear()
        return vcount

    def _get_unelected_quota_members(self, quota):
        """
        :return: Unelected members of `quota`
        :rtype: tuple
        """
        members = set(quota.members)
        return tuple(members.difference(set(self._elected)))

    def _initiate_new_count(self):
        """Performes a new count, elects, triggers quota-rules... etc."""
        logger.info("Initiating a new count (election number: %s)",
                    self._election_number)
        count_results = self._get_vcount_per_candidate()
        round_count_results = count_results.most_common()
        self._state.add_event(
            count.CountingEvent(count.CountingEventType.NEW_COUNT,
                                {'count_results': round_count_results}))
        self._vcount_results_remaining = collections.Counter(count_results)
        for vcount in round_count_results:
            candidate, candidate_count = vcount
            logger.info("Candidate %s: %s", candidate, candidate_count)
            if candidate_count >= self._election_number:
                # don't elect immediately here, because of debugging jazz.
                self._potentially_elected.append(candidate)
        # count performed
        if not self._potentially_elected:
            # Nobody to elect
            return
        if self._quotas_disabled:
            for candidate in list(self._potentially_elected):
                self._elect_candidate(candidate)
            return
        for candidate in list(self._potentially_elected):
            if self._max_quota_full(candidate):
                logger.info(
                    "Candidate %s can not be elected because one of its "
                    "quota-groups has reached its max-value. "
                    "Eliminating instead in the next round according to §29.",
                    candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.DENY_ELECT_QUOTA_MAX,
                        {'candidate': str(candidate.id)}))
                continue
            duplicates = self._get_candidates_with_duplicate_scores(
                candidate,
                self._potentially_elected)
            if not duplicates:
                self._elect_candidate(candidate)
                continue
            if self._can_be_elected_together((candidate, ) + duplicates):
                self._elect_candidate(candidate)
                for duplicate in duplicates:
                    self._elect_candidate(duplicate)
            else:
                logger.info(
                    "%d candidates with the same score (%s) "
                    "that can not be elected together.",
                    len(duplicates) + 1,
                    count_results[candidate])
                drawing_candidates = (candidate, ) + duplicates
                for drawing_candidate in drawing_candidates:
                    logger.info("Candidate %s", drawing_candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.SAME_SCORE,
                        {'candidates': [str(cand.id) for cand in
                                        drawing_candidates],
                         'identical_score': str(count_results[candidate])}))
                logger.info(
                    "Drawing candidate to elect in accordance with §29.")
                drawn_candidate = self._counter_obj.draw_candidate(
                    drawing_candidates)
                logger.info("Electing candidate %s", drawn_candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.DRAW_SELECT,
                        {'candidate': str(drawn_candidate.id)}))
                self._elect_candidate(drawn_candidate)

    def _max_quota_full(self, candidate, elected=None):
        """
        Checks for §26 conditions

        :param candidate: Candidate object
        :type candidate: object

        :param elected: Alternative sequence to self._elected (default: None)
        :type elected: collections.abc.Sequence

        :return: Tuple of quota-objects that have reached max_value and where
                 `candidate` is a member
        :rtype: tuple
        """
        if self._quotas_disabled:
            logger.debug("No quota-groups defined")
            return tuple()
        if elected is None:
            elected = self._elected
        quota_groups = self._get_candidate_quota_groups(candidate)
        if not quota_groups:
            # Implement implicit min_value = 0 in the future
            logger.debug("%s is not member of any quota-group(s)", candidate)
            return tuple()
        full_groups = []
        for quota_group in quota_groups:
            members = set(quota_group.members)
            max_value = self._counter_obj.max_choosable(quota_group)
            sum_elected_members = len(members.intersection(set(elected)))
            if sum_elected_members >= max_value:
                full_groups.append(quota_group)
        return tuple(full_groups)

    def _min_quota_required(self, candidate):
        """
        Checks for §27 conditions

        If `candidate` must be elected in order for the quota group she is
        member of to fulfill its min_value, this method will return True

        :param candidate: Candidate object
        :type candidate: object

        :return: Election required
        :rtype: bool
        """
        if self._quotas_disabled:
            logger.debug("No quota-groups defined")
            return False
        quota_groups = self._get_candidate_quota_groups(candidate)
        if not quota_groups:
            logger.debug("%s is not member of any quota-group(s)", candidate)
            return False
        for quota_group in quota_groups:
            members = set(quota_group.members)
            sum_remaining_members = len(members.intersection(
                self._get_remaining_candidates()))
            sum_elected_members = len(members.intersection(set(self._elected)))
            if (
                    sum_remaining_members <=
                    quota_group.min_value - sum_elected_members
            ):
                return True
        return False

    def _set_ballot_new_owner(self, ballot, candidate):
        """
        Transfers the ownership of `ballot` to `candidate`

        N.B. The state records must be updated suparately
        """
        current_owner = self._ballot_owners[ballot]
        self._candidate_ballots[current_owner].pop(
            self._candidate_ballots[current_owner].index(ballot))
        self._candidate_ballots[candidate].append(ballot)
        self._ballot_owners[ballot] = candidate

    def _set_initial_ballot_state(self):
        """Sets the initial state of the ballots based on §18.2"""
        # candidate: list of ballots - dict
        candidate_ballots = collections.defaultdict(list)
        transferred_candidate_ballots = collections.defaultdict(list)
        ballot_owner = {}  # ballot: candidate - dict
        ballot_weight = collections.Counter()  # ballot: weight - dict
        for ballot in self._counter_obj.ballots:
            if not ballot.candidates:
                # blank ballot
                continue
            candidate_ballots[ballot.candidates[0]].append(ballot)
            transferred_candidate_ballots[ballot.candidates[0]].append(ballot)
            ballot_owner[ballot] = ballot.candidates[0]
            ballot_weight[ballot] = ballot.pollbook.weight_per_pollbook
        for candidate in self._counter_obj.candidates:
            if candidate not in candidate_ballots:
                candidate_ballots[candidate] = list()
                transferred_candidate_ballots[candidate] = list()
        self._candidate_ballots = dict(candidate_ballots)
        self._state.update_transferred_candidate_ballots(
            transferred_candidate_ballots)
        self._transferred_uncounted_ballots.update(candidate_ballots)
        self._ballot_weights = ballot_weight
        self._state.update_transferred_ballot_weights(ballot_weight)
        self._ballot_owners = ballot_owner
        # self._state.update_transferred_ballot_owners(ballot_owner)

    def _terminate_regular_count(self):
        """
        Terminates the entire count of regular candidates.

        This method is a wrapper and should only be invoked in self.count
        from a `return` statement

        :return: The last state
        :rtype: RoundState
        """
        self._state.final = True
        logger.info("Regular count completed")
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TERMINATE_REGULAR_COUNT, {}))
        if not self._counter_obj.election.num_substitutes:
            logger.debug("No substitute candidates to be elected. "
                         "Election count completed.")
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NO_ELECTABLE_SUBSTITUTES, {}))
            return self._state
        if len(self._counter_obj.candidates) == len(self._elected):
            logger.debug(
                "Not enough unelected candidates for a substitute-round. "
                "Election count completed.")
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NOT_ENOUGH_FOR_SUBSTITUTE_ROUND,
                    {}))
            return self._state
        # some testing functionality may want to abort here
        if self._counter_obj.regular_count_only:
            logger.info("Regular count only. "
                        "Explicitly aborting after the regular round")
            return self._state
        logger.debug("-" * 8)
        logger.debug("-" * 8)
        logger.info("Starting substitute count")
        new_substitute_round = SubstituteRound(self._counter_obj, self)
        return new_substitute_round.count()

    def _transfer_ballots_from_excluded_candidates(self):
        """Implements most of §17"""
        # §17.2
        weight_groups = collections.defaultdict(list)
        excluded_candidates_data = []  # used for the event only
        for excluded_candidate in self._state.excluded:
            group_counter = collections.Counter()  # debugging
            all_ballots, tballots = self._get_candidate_transferrable_ballots(
                excluded_candidate,
                from_election_state=False)
            for ballot in tballots:
                weight_groups[self._ballot_weights[ballot]].append(ballot)
                group_counter[self._ballot_weights[ballot]] += 1
            logger.info("%s has %d ballot(s) in %d group(s) to transfer "
                        "as well as %d blank ballot(s)",
                        excluded_candidate,
                        len(tballots),
                        len(group_counter),
                        len(all_ballots) - len(tballots))
            # just some debugging
            keys = list(group_counter.keys())
            keys.sort(reverse=True)
            for key in keys:
                logger.info("group weight: %s -> %d",
                            key,
                            group_counter[key])
            excluded_candidates_data.append({
                'excluded_candidate': str(excluded_candidate.id),
                'ballots_count': len(tballots),
                'groups_count': len(group_counter),
                'empty_ballots_count': (len(all_ballots) - len(tballots)),
                'groups': [tuple([str(w), group_counter[w]]) for w in keys]})
        group_keys = list(weight_groups.keys())
        if len(group_keys) > 1:
            group_keys.sort(reverse=True)
            logger.info("Several weight groups exist: %s", str(group_keys))
        if excluded_candidates_data:
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TRANSFER_BALLOTS_FROM_EXCL_CAND,
                    {'excluded_candidates_data': excluded_candidates_data,
                     'weight_groups': [str(wg) for wg in group_keys]}))
        # §17.3, §17.4
        for key in group_keys:
            logger.info("Transferring ballots with weight: %s", key)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TRANSFERRING_BALLOTS_WITH_WEIGHT,
                    {'weight': str(key)}))
            self._transfer_excluded_ballots_to_remaining_candidates(
                weight_groups[key])
            logger.info("Initiating new count after transferring ballots")
            self._initiate_new_count()

    def _transfer_excluded_ballots_to_remaining_candidates(self, ballots):
        """§17.3"""
        ballot_owners = self._get_new_owners(ballots)
        new_transferred_ballot_weights = collections.Counter()
        new_candidate_ballots = collections.defaultdict(list)
        new_transferred_candidate_ballots = collections.defaultdict(list)
        for ballot, new_owner in ballot_owners.items():
            # no change in weights, but we need to set them anyway
            new_transferred_ballot_weights[ballot] = (
                self._ballot_weights[ballot])
            new_candidate_ballots[new_owner].append(ballot)
            new_transferred_candidate_ballots[new_owner].append(ballot)
            self._set_ballot_new_owner(ballot, new_owner)
        self._state.update_transferred_ballot_weights(
            new_transferred_ballot_weights)
        # self._state.update_transferred_ballot_owners(ballot_owners)
        self._state.update_transferred_candidate_ballots(
            new_transferred_candidate_ballots)
        self._transferred_uncounted_ballots.update(new_candidate_ballots)
        transfer_list = []
        for receiver, tballots in new_transferred_candidate_ballots.items():
            tweight = sum(map(lambda b: new_transferred_ballot_weights[b],
                              tballots))
            logger.info("%s received %d ballot(s) with total weight %s",
                        receiver,
                        len(tballots),
                        tweight)
            transfer_list.append({'receiver': str(receiver.id),
                                  'ballot_count': len(tballots),
                                  'total_ballot_weight': str(tweight)})
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TRANSFER_EBALLOTS_TO_REMAINING_CAND,
                {'transfer_list': transfer_list}))

    def _transfer_surplus(self, candidate):
        """
        Transfers the ballots of the elected `candidate`.

        Important implementation of §18,

        :param candidate: The candidate object
        :type candidate: object
        """
        logger.info("Transfering surplus of the elected candidate: %s",
                    candidate)
        all_ballots, transferrable_ballots = (
            self._get_candidate_transferrable_ballots(
                candidate,
                from_election_state=True))
        transferred_ballot_weights = self._get_transferred_ballot_weights(
            candidate)
        total_transferrable_ballot_weight = sum(
            map(lambda b: transferred_ballot_weights[b],
                transferrable_ballots))
        len_transferrable_ballots = len(transferrable_ballots)
        logger.info("Transferrable ballots: %d", len_transferrable_ballots)
        logger.info("Blank ballots: %d",
                    len(all_ballots) - len_transferrable_ballots)
        logger.info("Transferrable ballot weight: %s",
                    total_transferrable_ballot_weight)
        cand_surplus = self._surplus_per_elected_candidate[candidate]
        logger.info("Candidate surplus: %s", cand_surplus)
        # §18.3
        if total_transferrable_ballot_weight > cand_surplus:
            logger.info("Transferrable ballot weight > candidate surplus")
            quotient = (
                cand_surplus /
                decimal.Decimal(len_transferrable_ballots)).quantize(
                    decimal.Decimal('1.00'),
                    decimal.ROUND_DOWN)
            logger.info("quotient: %s / %s = %s",
                        cand_surplus,
                        len_transferrable_ballots,
                        quotient)
        else:
            logger.info("Transferrable ballot weight <= candidate surplus")
            quotient = decimal.Decimal(1)
            logger.info("quotient: 1")
        # §18.4
        ballot_owners = self._get_new_owners(transferrable_ballots)
        new_transferred_ballot_weights = collections.Counter()
        new_candidate_ballots = collections.defaultdict(list)
        new_transferred_candidate_ballots = collections.defaultdict(list)
        for ballot, new_owner in ballot_owners.items():
            self._ballot_weights[ballot] = (
                transferred_ballot_weights[ballot] * quotient)
            new_transferred_ballot_weights[ballot] = (
                transferred_ballot_weights[ballot] * quotient)
            new_candidate_ballots[new_owner].append(ballot)
            new_transferred_candidate_ballots[new_owner].append(ballot)
            self._set_ballot_new_owner(ballot, new_owner)
        self._state.update_transferred_candidate_ballots(
            new_transferred_candidate_ballots)
        self._transferred_uncounted_ballots.update(new_candidate_ballots)
        self._state.update_transferred_ballot_weights(
            new_transferred_ballot_weights)
        # self._state.update_transferred_ballot_owners(ballot_owners)
        logger.info("Transferring surplus from candidate: %s", candidate)
        transfer_list = []
        for receiver, ballots in new_transferred_candidate_ballots.items():
            tweight = sum(map(lambda b: new_transferred_ballot_weights[b],
                              ballots))
            logger.info("%s received %d ballot(s) with total weight %s",
                        receiver,
                        len(ballots),
                        tweight)
            transfer_list.append({'receiver': str(receiver.id),
                                  'ballot_count': len(ballots),
                                  'total_ballot_weight': str(tweight)})
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TRANSFER_SURPLUS,
                {'transfer_list': transfer_list,
                 'candidate': str(candidate.id),
                 'transferrable_ballots_count': len_transferrable_ballots,
                 'blank_ballots_count': (
                     len(all_ballots) - len_transferrable_ballots),
                 'candidate_surplus': str(cand_surplus),
                 'quotient': str(quotient),
                 'total_transferrable_ballot_weight': str(
                     total_transferrable_ballot_weight)}))

    def _update_quota_status(self):
        """
        Updates the quota status for regular candidates.

        Re-checks and if necessary disables quota-checks for the
        regular counts. This method should only be called before
        the start of the regular count.
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

    def _update_surplus_for_elected_candidate(self, candidate):
        """Updates the surplus for `candidate` after she is elected"""
        if candidate not in self._elected:
            raise count.CountingFailure(
                'Can not update the surplus of unelected candidate')
        if not self._vcount_results_remaining:
            logger.warning("No counting performed yet. "
                           "Unable to calculate surplus for %s",
                           candidate)
            return
        if candidate not in self._vcount_results_remaining:
            logger.debug("Candidate %s not in the count results mapping",
                         candidate)
            return
        surplus = (self._vcount_results_remaining[candidate] -
                   self._election_number)
        if surplus < 0:  # elected for other reasons than vcount
            # should not happen?
            surplus = decimal.Decimal(0)
        self._surplus_per_elected_candidate[candidate] = surplus
        logger.info("Calculated surplus for %s: %s",
                    str(candidate),
                    surplus)
        self._state.add_event(
            count.CountingEvent(count.CountingEventType.UPDATE_SURPLUS,
                                {'candidate': str(candidate.id),
                                 'new_surplus': str(surplus)}))


class SubstituteRound(RegularRound):
    """
    Substitute round class.

    Represents a single counting round for a substitute round.
    """

    def __init__(self, counter, parent=None):
        """
        :param counter: Counter-object
        :type counter: UiOSTVCounter

        :param parent: The parent (recursive) object
        :type parent: RegularRound, SubstituteRound or None
        """
        self._round_cnt = 1
        self._round_id = 1
        self._substitute_nr = 1  # substitute currently elected (number)
        self._counter_obj = counter
        self._parent = parent
        self._elected = []  # all elected candidates (regular + substitutes)
        self._elected_substitutes = []  # all elected substitutes
        self._potentially_elected = []
        # elected in an earlier round, but still counted here
        # because of surplus
        self._elected_earlier = []
        self._excluded = []
        self._first_substitute_count = False  # first substitute count
        # candidate: ballots-list - dict
        self._transferred_uncounted_ballots = {}
        # the vote count of the remaining candidates
        self._vcount_results_remaining = collections.Counter()
        self._surplus_per_elected_candidate = collections.Counter()
        self._state = RoundState(self)
        self._counter_obj.append_state_to_current_path(self._state)
        if self._parent is None:
            # There were no regular round(s)
            self._quotas_disabled = not bool(self._counter_obj.quotas)
            self._first_substitute_count = True
            if self._counter_obj.regular_count_only:
                logger.warning(
                    "Regular count only can not be enforced for this election")
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_SUBSTITUTE_ROUND,
                    {'round_id': self._round_id,
                     'election_number': '',
                     'elected_count': 0,
                     'sum_surplus': '0',
                     'remaining_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates)]),
                     'candidates_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates)]),
                     'substitute_nr': self._substitute_nr,
                     'round_count': self._round_cnt}))
            self._election_number = self._get_election_number()
            self._set_initial_ballot_state()
        elif not isinstance(self._parent, SubstituteRound):
            # The first round after a regular round
            self._elected = list(self._parent.elected)
            self._round_cnt = self._parent.round_cnt + 1
            self._first_substitute_count = True
            # re-evaluate disableing quota-rules from scratch
            self._quotas_disabled = not bool(self._counter_obj.quotas)
            self._update_quota_values()
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_SUBSTITUTE_ROUND,
                    {'round_id': self._round_id,
                     'election_number': '',
                     'elected_count': 0,
                     'sum_surplus': '0',
                     'remaining_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates) -
                          len(self._elected)]) - len(
                              self._elected_substitutes),
                     'candidates_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates) -
                          len(self._elected)]),
                     'substitute_nr': self._substitute_nr,
                     'round_count': self._round_cnt}))
            self._election_number = self._get_election_number()
            self._set_initial_ballot_state()
        elif self._parent.state.substitute_final:
            # New substitute count
            self._round_cnt = self._parent.round_cnt + 1
            self._substitute_nr = self._parent.substitute_nr + 1
            self._elected = list(self._parent.elected)
            self._elected_substitutes = list(self._parent.elected_substitutes)
            self._first_substitute_count = True
            self._quotas_disabled = self._parent.quotas_disabled
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_SUBSTITUTE_ROUND,
                    {'round_id': self._round_id,
                     'election_number': '',
                     'elected_count': len(self._elected_substitutes),
                     'sum_surplus': '0',
                     'remaining_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates) -
                          len(self._elected)]) - len(
                              self._elected_substitutes),
                     'candidates_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates) -
                          len(self._elected)]),
                     'substitute_nr': self._substitute_nr,
                     'round_count': self._round_cnt}))
            self._election_number = self._get_election_number()
            self._set_initial_ballot_state()
        else:
            # New round, old count
            self._round_cnt = self._parent.round_cnt + 1
            self._round_id = self._parent.round_id + 1
            self._substitute_nr = self._parent.substitute_nr
            self._elected = list(self._parent.elected)
            self._elected_substitutes = list(self._parent.elected_substitutes)
            self._elected_earlier = list(self._parent.elected_earlier)
            self._excluded = list(self._parent.excluded)
            self._election_number = self._parent.election_number
            self._quotas_disabled = self._parent.quotas_disabled
            self._vcount_results_remaining = collections.Counter(
                self._parent.vcount_results_remaining)
            self._surplus_per_elected_candidate = collections.Counter(
                self._parent.surplus_per_elected_candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.NEW_SUBSTITUTE_ROUND,
                    {'round_id': self._round_id,
                     'election_number': str(self._election_number),
                     'elected_count': len(self._elected_substitutes),
                     'sum_surplus': str(self._get_total_surplus()),
                     'remaining_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates) -
                          len(self._elected)]) - len(
                              self._elected_substitutes),
                     'candidates_to_elect_count': min(
                         [self._counter_obj.election.num_substitutes,
                          len(self._counter_obj.candidates) -
                          len(self._elected)]),
                     'substitute_nr': self._substitute_nr,
                     'round_count': self._round_cnt}))
            self._ballot_weights = collections.Counter(
                self._parent.ballot_weights)
            self._candidate_ballots = dict(self._parent.candidate_ballots)
            self._ballot_owners = dict(self._parent.ballot_owners)
            self._transferred_uncounted_ballots = dict(
                self._parent.transferred_uncounted_ballots)
        if self._round_cnt > 1000:
            logger.critical('Infinite recursion caught. Killing everything...')
            raise count.CountingFailure(
                'Infinite recursion caught in regular round')

    @property
    def substitute_nr(self):
        """substitute_nr-property"""
        return self._substitute_nr

    @property
    def elected_earlier(self):
        """elected_earlier-property"""
        return self._elected_earlier

    @property
    def elected_substitutes(self):
        """elected_substitutes-property"""
        return self._elected_substitutes

    def count(self):
        """
        Performs the actual count.

        This method will either return a final state or call itself on a newly
        instanciated object. (resurse until final state is returned)

        :return: A state (result) for this count
        :rtype: RoundState
        """
        logger.debug("---")
        logger.info("Counting substitute %d round: %d (%d)",
                    self._substitute_nr,
                    self._round_id,
                    self._round_cnt)
        logger.info("Election number: %s",
                    self._election_number)
        # §19 - start by checking termination criteria
        logger.debug("Checking §19")
        if (
                self._first_substitute_count and
                not self._counter_obj.election.num_substitutes
        ):
            logger.info(
                "No substitute candidates to be elected. Terminating count.")
            return self._terminate_substitute_count()
        try:
            self._check_total_remaining_candidates()  # 19.1
            self._check_remaining_candidates()  # §19.1
            self._check_election_quota_reached()  # §19.2
            logger.debug("Checking §19 - done")
            if self._first_substitute_count:
                # First substitute, first round
                logger.debug("First round. No surplus here.")
                self._initiate_new_count()
                new_round = SubstituteRound(self._counter_obj, self)
                return new_round.count()
            # calculate surplus
            total_surplus = self._get_total_surplus()
            logger.info("Total surplus from %d elected candidate(s) "
                        "from previous round(s): %s",
                        len(self._surplus_per_elected_candidate),
                        total_surplus)
            # §16.3 - check if someone can be excluded,
            # but §21 comes into play here as well.
            results_remaining = collections.Counter(
                self._vcount_results_remaining)
            while True:
                # avoid infinite loop in case some miracle happens
                if not results_remaining:
                    excludable_candidates = tuple()
                    break
                try:
                    excludable_candidates = self._get_excludable_candidates(
                        results_remaining.most_common())
                    break
                except NoMoreExcludableCandidates:
                    # pop the bottom candidate and try again
                    results_remaining.pop(
                        results_remaining.most_common()[-1][0])
                    continue
            if not excludable_candidates:
                logger.debug("No candidates for exclusion")
                self._state.add_event(count.CountingEvent(
                    count.CountingEventType.UNABLE_TO_EXCLUDE, {}))
                # §16.4 - check if there is any remaining surplus
                if self.has_remaining_surplus:
                    # §16.4 - A
                    surplus_items = self._get_greatest_surplus()
                    if len(surplus_items) > 1:
                        logger.info("%d candidates have the same and greatest "
                                    "surplus of %s",
                                    len(surplus_items),
                                    surplus_items[0][1])
                        surplus_candidates = []
                        for surplus_item in surplus_items:
                            surplus_candidates.append(surplus_item[0])
                            logger.info("Candidate %s", surplus_item[0])
                        logger.info("Drawing candidate whos surplus to "
                                    "transfer in accordance with §16.4 - A")
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.SAME_SURPLUS,
                                {'candidates': [str(cand.id) for cand in
                                                surplus_candidates],
                                 'identical_surplus': str(
                                     surplus_items[0][1])}))
                        drawn_candidate = self._counter_obj.draw_candidate(
                            surplus_candidates)
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.DRAW_SELECT,
                                {'candidate': str(drawn_candidate.id)}))
                        logger.info("Transferring the surplus of candidate %s",
                                    drawn_candidate)
                        self._transfer_surplus(drawn_candidate)
                        self._clear_candidate_surplus(drawn_candidate)
                    else:
                        surplus_candidate = surplus_items[0][0]
                        self._transfer_surplus(surplus_candidate)
                        self._clear_candidate_surplus(surplus_candidate)
                else:
                    logger.info(
                        "No available surplus. "
                        "Excluding candidates at the bottom (§16.4-B)")
                    bottom_candidates = self._get_filtered_excludables(
                        self._get_bottom_candidates())
                    if not bottom_candidates:
                        # all bottom candidates are "quota-protected"
                        logger.warning("No bottom candidates to exclude. "
                                       "Starting a new round")
                        cresults = self._vcount_results_remaining.most_common()
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.DISPLAY_STATUS,
                                {'count_results': cresults}))
                        new_round = SubstituteRound(self._counter_obj,
                                                    self)
                        return new_round.count()
                    if len(bottom_candidates) == 1:
                        # great! only one bottom candidate not protected
                        # by quota-rule or §21
                        logger.info("Excluding: %s", bottom_candidates[0])
                        self._exclude_candidate(bottom_candidates[0])
                        self._check_remaining_candidates()
                    else:  # > 1 bottom_candidates to exclude
                        logger.info("%d bottom candidates to exclude.",
                                    len(bottom_candidates))
                        for bottom_candidate in bottom_candidates:
                            logger.info(
                                "Candidate %s: %s",
                                bottom_candidate,
                                self._vcount_results_remaining[
                                    bottom_candidate])
                        logger.info("Drawing candidate to exclude in "
                                    "accordance with §16.4 - B.")
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.BOTTOM_SCORE,
                                {'candidates': [str(cand.id) for cand in
                                                bottom_candidates],
                                 'identical_score': str(
                                     self._vcount_results_remaining[
                                         bottom_candidates[0]])}))
                        drawn_candidate = self._counter_obj.draw_candidate(
                            bottom_candidates)
                        logger.info("Candidate %s was drawn for exclusion.",
                                    drawn_candidate)
                        self._state.add_event(
                            count.CountingEvent(
                                count.CountingEventType.DRAW_SELECT,
                                {'candidate': str(drawn_candidate.id)}))
                        self._exclude_candidate(drawn_candidate)
                        self._check_remaining_candidates()
            for excludable_candidate in excludable_candidates:
                logger.info("Excluding: %s", excludable_candidate)
                self._exclude_candidate(excludable_candidate)
            # check §19.1 again
            self._check_total_remaining_candidates()
            self._check_remaining_candidates()
            self._transfer_ballots_from_excluded_candidates()
            if not excludable_candidates:
                self._initiate_new_count()
            new_round = SubstituteRound(self._counter_obj, self)
            return new_round.count()
        except SubstituteCandidateElected:
            logger.info("Terminating election of substitute %d",
                        self._substitute_nr)
            return self._terminate_substitute_election()
        except NoMoreElectableCandidates:
            # §19.1
            logger.info("§19.1 Remaining candidates <= electable candidates")
            self._state.paragraph_19_1 = True
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TERMINATE_19_1, {}))
            remaining_candidates = tuple(
                set(self._get_remaining_candidates()).difference(
                    set(self._elected)))
            if remaining_candidates:
                # only one remaining candidate
                try:
                    self._elect_candidate(remaining_candidates[0])
                except SubstituteCandidateElected:
                    pass
                except RequiredCandidatesElected:
                    logger.info("All required candidates are elected. "
                                "Terminating count according to §19.2.")
                    self._state.add_event(
                        count.CountingEvent(
                            count.CountingEventType.TERMINATE_19_2, {}))
                    return self._terminate_substitute_count()
            return self._terminate_substitute_election()
        except NoMoreGloballyElectableCandidates:
            # §19.1 - same as above, only result of a "global" check
            # Only one last candidate remains unelected
            logger.info("Only one globally unelected candidate remains. "
                        "Electing according to §19.1.")
            self._state.paragraph_19_1 = True
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TERMINATE_19_1, {}))
            try:
                self._elect_candidate(
                    self._get_globally_unelected_candidates()[0])
            except SubstituteCandidateElected:
                pass
            except NoMoreElectableCandidates:
                pass
            except RequiredCandidatesElected:
                logger.info("All required candidates are elected. "
                            "Terminating count according to §19.2.")
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.TERMINATE_19_2, {}))
            return self._terminate_substitute_count()
        except RequiredCandidatesElected:
            # §19.2
            logger.info("All required candidates are elected. "
                        "Terminating count according to §19.2.")
            self._state.add_event(
                count.CountingEvent(count.CountingEventType.TERMINATE_19_2,
                                    {}))
            return self._terminate_substitute_count()

    def __str__(self):
        return ('SubstituteRound: {substitute_nr}-{id}/'
                '{total_count}'.format(
                    substitute_nr=self._substitute_nr,
                    id=self._round_id,
                    total_count=self._round_cnt))

    def _check_election_quota_reached(self):
        """§19.2"""
        minimum_group = min([(self._counter_obj.election.num_choosable +
                              self._counter_obj.election.num_substitutes),
                             len(self._counter_obj.candidates)])
        if len(self._elected) == minimum_group:
            raise RequiredCandidatesElected
        return False

    def _check_remaining_candidates(self):
        """§19.1"""
        if (
                len(set(self._get_remaining_candidates()).difference(
                    set(self._elected))) <= 1
        ):
            raise NoMoreElectableCandidates
        return True

    def _check_total_remaining_candidates(self):
        """§19.1"""
        if len(self._get_globally_unelected_candidates()) <= 1:
            raise NoMoreGloballyElectableCandidates
        return True

    def _elect_candidate(self, candidate):
        """Wraps the functionality of electing a candidate"""
        last_substitute_candidate = len(
            self._get_globally_unelected_candidates()) <= 1
        if candidate in self._state.quota_excluded:
            logger.debug("Candidate %s is excluded based on quota. "
                         "Unable to elect",
                         candidate)
            return
        if candidate in self._excluded:
            logger.error("Candidate %s is marked as excluded. Unable to elect",
                         candidate)
            return
        if candidate in self._elected:
            logger.info("Candidate %s is elected in a previous round",
                        candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.CANDIDATE_ELECTED_EARLIER,
                    {'candidate': str(candidate.id)}))
            if candidate in self._potentially_elected:
                self._potentially_elected.pop(
                    self._potentially_elected.index(candidate))
            if not self._state.paragraph_19_1:
                self._update_surplus_for_elected_candidate(candidate)
            if self._vcount_results_remaining.pop(candidate, None) is None:
                logger.warning(
                    "Candidate %s not found in vcount_results_remaining",
                    candidate)
            self._elected_earlier.append(candidate)
            # update the state as if it is a normal election because of
            # transferring surplus
            self._state.add_elected_candidate(candidate)
            full_quota_groups = self._max_quota_full(candidate,
                                                     self._elected_substitutes)
            excludable_candidates = []
            for full_quota_group in full_quota_groups:
                unelected_members = self._get_unelected_quota_members(
                    full_quota_group)
                msg = 'Max-value for quota group {quota} is reached'.format(
                    quota=full_quota_group.name)
                if not unelected_members:
                    logger.debug(msg +
                                 ', but no unelected members. Continuing...')
                logger.debug(msg)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.MAX_QUOTA_VALUE_REACHED,
                        {'quota_group': full_quota_group.name,
                         'members': ([str(member.id) for
                                      member in unelected_members])}))
                excludable_candidates.extend(unelected_members)
            excludable_candidates = self._get_filtered_excludables(
                excludable_candidates)
            for excludable_candidate in excludable_candidates:
                logger.info("Candidate %s is member of a group that reached "
                            "its max. value. Excluding.",
                            excludable_candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.MAX_QUOTA_VALUE_EXCLUDED,
                        {'candidate': str(excludable_candidate.id)}))
                self._state.add_quota_excluded_candidate(excludable_candidate)
                self._exclude_candidate(excludable_candidate)
            if excludable_candidates:
                self._transfer_ballots_from_excluded_candidates()
            return
        self._elected_substitutes.append(candidate)
        self._elected.append(candidate)
        if candidate in self._potentially_elected:
            self._potentially_elected.pop(
                self._potentially_elected.index(candidate))
        logger.info("Candidate %s is elected", candidate)
        self._state.add_event(
            count.CountingEvent(
                (count.CountingEventType.CANDIDATE_ELECTED_19_1 if
                 self._state.paragraph_19_1 else
                 count.CountingEventType.CANDIDATE_ELECTED),
                {'candidate': str(candidate.id)}))
        if not last_substitute_candidate:
            if not self._state.paragraph_19_1:
                self._update_surplus_for_elected_candidate(candidate)
            if self._vcount_results_remaining.pop(candidate, None) is None:
                logger.warning("Candidate %s not in vcount_results_remaining",
                               candidate)
        self._state.add_elected_candidate(candidate)  # update the round-state
        self._state.all_elected_candidates = self._elected
        self._state.all_elected_substitutes = self._elected_substitutes
        self._check_election_quota_reached()
        raise SubstituteCandidateElected

    def _exclude_candidate(self, candidate):
        """Wraps the functionality of excluding a candidate"""
        # check §21 prohibiting the elimination of candidates
        # elected in earlier election counts.
        if candidate in self._elected:
            # this check should have been performed earlier. #paranoia, #debug
            logger.warning("Candidate %s was elected in an earlier election "
                           "count and can not be excluded here (§21)",
                           candidate)
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.ELECTED_EARLIER,
                    {'candidate': str(candidate.id)}))
            return None  # make pylint happy
        return super()._exclude_candidate(candidate)

    def _get_election_number(self):
        """
        Calculates the election-number for this round according to §20

        :return: The election number calculated for this round
        :rtype: decimal.Decimal
        """
        counting_ballot_pollbook = (
            [ballot.pollbook.weight_per_pollbook for
             ballot in self._counter_obj.counting_ballots])
        if len(counting_ballot_pollbook) < 10:
            # avoid log(0) and large epsilon when 1 <= ballots < 10
            prec = 2
        else:
            prec = 2 * int(math.log(len(counting_ballot_pollbook), 10))
        quotient_precision = decimal.Decimal(10) ** -prec  # §18.3, §33
        epsilon = decimal.Decimal((0, (1, ), -prec))
        weight_counting_ballots = decimal.Decimal(
            sum(counting_ballot_pollbook))
        quotient = (weight_counting_ballots /
                    decimal.Decimal(
                        self._counter_obj.election.num_choosable +
                        self._substitute_nr + 1)).quantize(
                            quotient_precision,
                            decimal.ROUND_DOWN)
        election_number = quotient + epsilon
        logger.debug("-" * 8)
        logger.info("Calculating election number:")
        logger.info("Quotient (§18.3, §33): "
                    "(%s (weight of counting ballots) / "
                    "(%s regular candidates to elect + (%s. substitute) + 1) "
                    "(with %d decimal precision) = %s",
                    weight_counting_ballots,
                    self._counter_obj.election.num_choosable,
                    self._substitute_nr,
                    prec,
                    quotient)
        logger.info("%s (quotient) + %s (epsilon) = %s",
                    quotient,
                    epsilon,
                    election_number)
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.ELECTION_NUMBER_SUBSTITUTE,
                {'weight_counting_ballots': str(weight_counting_ballots),
                 'candidates_to_elect': (
                     self._counter_obj.election.num_choosable),
                 'substitute_number': self._substitute_nr,
                 'precision': str(prec),
                 'quotient': str(quotient),
                 'epsilon': str(epsilon),
                 'election_number': str(election_number)}))
        return election_number

    def _get_excludable_candidates(self, results=None):
        """
        Important implementation of §16.3

        :return: Candidates that can be excluded based on a previous count
        :rtype: tuple
        """
        if self._first_substitute_count or not self._vcount_results_remaining:
            # first round or no counts in the previous round
            return tuple()
        if results is None:
            results = self._vcount_results_remaining.most_common()
        if len(results) < 2:
            # paranoia: this should not happen because of §19
            # that is always checked before exclusion
            return tuple()
        total_surplus = self._get_total_surplus()

        # §16.3 - D dictates that §16.3 - B is checked first and then §16.3 - A
        def sum_from(i):
            return sum(map(operator.itemgetter(1), results[i:]))

        largest_exclusion_group_size = 0
        for index, count_result in enumerate(results[:-1]):  # not the last one
            if sum_from(index + 1) + total_surplus < count_result[1]:
                largest_exclusion_group_size = len(results) - (index + 1)
                break
        else:
            # §16.3 - D
            return tuple()
        logger.info("§16.3 - D: Maximum to be excluded: %d",
                    largest_exclusion_group_size)
        # now check §16.3 - C
        max_possible_to_exclude = len(self._get_remaining_candidates()) - 1
        remaining_candidates_after_exclusion = (
            len(self._get_remaining_candidates()) -
            largest_exclusion_group_size)
        logger.info("§16.3 - C: Remaining candidates after exclusion: %d",
                    remaining_candidates_after_exclusion)
        if largest_exclusion_group_size <= max_possible_to_exclude:
            # return the largest possible group
            # make it look ugly because of debugging
            filtered_excludables = self._get_filtered_excludables(
                map(operator.itemgetter(0),
                    results[-largest_exclusion_group_size:]))
            if largest_exclusion_group_size and not filtered_excludables:
                logger.info("No candidates left to exclude after filtering "
                            "(§21 or §27)")
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.NO_EXCL_CANDIDATES_21,
                        {}))
                raise NoMoreExcludableCandidates
            return filtered_excludables
        # the candidates from exclusion are too many

        # pick a smaller size and perform the §16.3 - A check again!
        # Start with max_possible_to_exclude and if the test fails,
        # decrement the size by 1 and do it again
        # no candidates can be excluded if the size becomes 0
        while max_possible_to_exclude:
            if (
                    sum_from(-max_possible_to_exclude) + total_surplus <
                    results[-(max_possible_to_exclude + 1)][1]
            ):
                filtered_excludables = self._get_filtered_excludables(
                    map(operator.itemgetter(0),
                        results[-max_possible_to_exclude:]))
                if not filtered_excludables:
                    logger.info("No candidates left to exclude after "
                                "filtering (§21 or §27)")
                    self._state.add_event(
                        count.CountingEvent(
                            count.CountingEventType.NO_EXCL_CANDIDATES_21,
                            {}))
                    raise NoMoreExcludableCandidates
                return filtered_excludables
            max_possible_to_exclude -= 1
        # §16.3 - A didn't pass for any subgroup (size)
        # Nobody can be excluded here and now
        return tuple()

    def _get_filtered_excludables(self, excludables):
        """
        Implements §21 in addition to the filters implemented for regular round

        :return: The excludables the can actually be excluded
        :rtype: tuple
        """

        excludables = super()._get_filtered_excludables(excludables)
        filtered_excludables = []
        for excludable in excludables:
            # check §21 prohibiting the elimination of candidates elected in
            # earlier election counts.
            if excludable in self._elected:
                logger.info("Candidate %s was elected in an earlier election "
                            "count and can not be excluded here (§21)",
                            excludable)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.ELECTED_EARLIER,
                        {'candidate': str(excludable.id)}))
                continue
            filtered_excludables.append(excludable)
        return tuple(filtered_excludables)

    def _get_globally_unelected_candidates(self):
        """Returns all unelected candidates (globally)"""
        total = set(self._counter_obj.candidates)
        elected = set(self._elected)
        return tuple(total.difference(elected))

    def _get_remaining_candidates(self):
        """
        A tuple of remaining candidates for this substitute election

        :return: The remaining candidates
        :rtype: tuple
        """
        total = set(self._counter_obj.candidates)
        elected = set(self._elected_earlier)
        excluded = set(self._excluded)
        return tuple(total.difference(elected.union(excluded)))

    def _initiate_new_count(self):
        """Performes a new count, elects, triggers quota-rules... etc."""
        logger.info("Initiating a new count (election number: %s)",
                    self._election_number)
        count_results = self._get_vcount_per_candidate()
        round_count_results = count_results.most_common()
        self._state.add_event(
            count.CountingEvent(count.CountingEventType.NEW_COUNT,
                                {'count_results': round_count_results}))
        self._vcount_results_remaining = collections.Counter(count_results)
        for vcount in round_count_results:
            candidate, candidate_count = vcount
            logger.info("Candidate %s: %s", candidate, candidate_count)
            if candidate_count >= self._election_number:
                # don't elect immediately here, because of debugging jazz.
                self._potentially_elected.append(candidate)
        # count performed
        if not self._potentially_elected:
            # Nobody to elect
            return
        if self._quotas_disabled:
            for candidate in list(self._potentially_elected):
                self._elect_candidate(candidate)
            return
        for candidate in list(self._potentially_elected):
            # check if already elected (substitute round) before quota
            if candidate in self._elected:
                self._elect_candidate(candidate)
                continue
            if self._max_quota_full(candidate, self._elected_substitutes):
                logger.info(
                    "Candidate %s can not be elected because one of its "
                    "quota-groups has reached its max-value. "
                    "Eliminating instead in the next round according to §29.",
                    candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.DENY_ELECT_QUOTA_MAX,
                        {'candidate': str(candidate.id)}))
                continue
            duplicates = self._get_candidates_with_duplicate_scores(
                candidate,
                self._potentially_elected)
            if not duplicates:
                self._elect_candidate(candidate)
                continue
            if (
                    self._can_be_elected_together((candidate, ) + duplicates,
                                                  self._elected_substitutes)
            ):
                self._elect_candidate(candidate)
                for duplicate in duplicates:
                    self._elect_candidate(duplicate)
            else:
                logger.info(
                    "%d candidates with the same score (%s) "
                    "that can not be elected together.",
                    len(duplicates) + 1,
                    count_results[candidate])
                drawing_candidates = (candidate, ) + duplicates
                for drawing_candidate in drawing_candidates:
                    logger.info("Candidate %s", drawing_candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.SAME_SCORE,
                        {'candidates': [str(cand.id) for cand in
                                        drawing_candidates],
                         'identical_score': str(count_results[candidate])}))
                logger.info(
                    "Drawing candidate to elect in accordance with §29.")
                drawn_candidate = self._counter_obj.draw_candidate(
                    drawing_candidates)
                logger.info("Electing candidate %s", drawn_candidate)
                self._state.add_event(
                    count.CountingEvent(
                        count.CountingEventType.DRAW_SELECT,
                        {'candidate': str(drawn_candidate.id)}))
                self._elect_candidate(drawn_candidate)

    def _max_quota_full(self, candidate, elected=None):
        """
        Checks for §26 conditions

        :param candidate: Candidate object
        :type candidate: object

        :param elected: Alternative sequence to self._elected (default: None)
        :type elected: collections.abc.Sequence

        :return: Tuple of quota-objects that have reached max_value and where
                 `candidate` is a member
        :rtype: tuple
        """
        if self._quotas_disabled:
            logger.debug("No quota-groups defined")
            return tuple()
        if elected is None:
            elected = self._elected
        quota_groups = self._get_candidate_quota_groups(candidate)
        if not quota_groups:
            # Implement implicit min_value = 0 in the future
            logger.debug("%s is not member of any quota-group(s)", candidate)
            return tuple()
        full_groups = []
        for quota_group in quota_groups:
            members = set(quota_group.members)
            max_value = self._counter_obj.max_substitutes(quota_group)
            sum_elected_members = len(members.intersection(set(elected)))
            if sum_elected_members >= max_value:
                full_groups.append(quota_group)
        return tuple(full_groups)

    def _min_quota_required(self, candidate):
        """
        Checks for §27 conditions

        If `candidate` must be elected in order for the quota group she is
        member of to fulfill its min_value, this method will return True

        :param candidate: Candidate object
        :type candidate: object

        :return: Election required
        :rtype: bool
        """
        if self._quotas_disabled:
            logger.debug("No quota-groups defined")
            return False
        quota_groups = self._get_candidate_quota_groups(candidate)
        if not quota_groups:
            logger.debug("%s is not member of any quota-group(s)", candidate)
            return False
        for quota_group in quota_groups:
            # remaining candidates to elect = remaining elections
            remaining_elections = (self._counter_obj.election.num_substitutes -
                                   self._substitute_nr +
                                   1)
            members = set(quota_group.members)
            # for §27 purposes we do not count previously elected quota members
            remaining_candidates = set(
                self._get_remaining_candidates()).difference(set(
                    self._elected))
            sum_remaining_members = len(
                members.intersection(remaining_candidates))
            sum_elected_substitutes = len(members.intersection(set(
                self._elected_substitutes)))
            if not sum_remaining_members:
                logger.debug("Quota group %s has no more remaining members",
                             quota_group)
                continue
            diff = quota_group.min_value_substitutes - sum_elected_substitutes
            if (
                    sum_remaining_members == 1 and
                    diff >= remaining_elections
            ):
                return True
        return False

    def _terminate_substitute_count(self):
        """
        Terminates the entire count of regular candidates.

        This method is a wrapper and should only be invoked in self.count
        from a `return` statement

        :return: The last state
        :rtype: RoundState
        """
        self._state.substitute_final = True
        self._state.final = True
        logger.info("Substitute count completed")
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TERMINATE_SUBSTITUTE_COUNT,
                {'substitute_nr': self._substitute_nr}))
        return self._state

    def _terminate_substitute_election(self):
        """
        Terminates only the the election of the current substitute candidate.

        This method is a wrapper and should only be invoked in self.count
        from a `return` statement

        :return: The last state
        :rtype: RoundState
        """
        self._state.substitute_final = True
        logger.info("Substitute %d election completed", self._substitute_nr)
        self._state.add_event(
            count.CountingEvent(
                count.CountingEventType.TERMINATE_SUBSTITUTE_ELECTION,
                {'substitute_nr': self._substitute_nr}))
        try:
            # now check if the entire substitute count is done
            self._check_election_quota_reached()
            new_round = SubstituteRound(self._counter_obj, self)
            return new_round.count()
        except RequiredCandidatesElected:
            logger.info("All required candidates are elected. "
                        "Terminating count according to §19.2.")
            self._state.add_event(
                count.CountingEvent(
                    count.CountingEventType.TERMINATE_19_2, {}))
            return self._terminate_substitute_count()

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
        return None  # please pylint
