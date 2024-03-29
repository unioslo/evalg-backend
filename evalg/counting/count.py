# -*- coding: utf-8 -*-
"""Tools for counting elections"""
import collections
import datetime
import decimal
import enum
import logging
import operator
import os
import random
import secrets

import pytz

from evalg.counting.algorithms import (
    ntnucv,
    mntv,
    uiostv,
    uiomv,
    uitstv,
    poll,
    party_list,
    positional_voting,
)


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)

PROTOCOL_MAPPINGS = {
    "uio_stv": uiostv.Protocol,
    "uit_stv": uitstv.Protocol,
    "uio_mv": uiomv.Protocol,
    "mntv": mntv.Protocol,
    "ntnu_cv": ntnucv.Protocol,
    "poll": poll.Protocol,
    "sainte_lague": party_list.Protocol,
    "uio_sainte_lague": party_list.Protocol,
    "positional_voting": positional_voting.Protocol,
}
RESULT_MAPPINGS = {
    'uio_stv': uiostv.Result,
    'uio_mv': uiomv.Result,
    'mntv': mntv.Result,
    'ntnu_cv': ntnucv.Result,
    'poll': poll.Result,
}

class CountingFailure(Exception):
    """General custom exception"""


class CountingEventType(enum.Enum):
    """The counting event types"""
    # candidates with the same score that can not be excluded together
    BOTTOM_SCORE = enum.auto()

    # candidate has been elected
    CANDIDATE_ELECTED = enum.auto()

    # candidate has been elected because of §19.1
    CANDIDATE_ELECTED_19_1 = enum.auto()

    # candidate has been elected in a previous round
    CANDIDATE_ELECTED_EARLIER = enum.auto()

    # candidate has been excluded
    CANDIDATE_EXCLUDED = enum.auto()

    # the candidate must be elected in order to fulfill the quota-rules
    CANDIDATE_QUOTA_PROTECTED = enum.auto()

    # two or more candidates can not be excluded together because of min. quota
    CANT_BE_EXCLUDED_TOGETHER = enum.auto()

    # candidate can not be elected because one of her groups has reached max.v.
    DENY_ELECT_QUOTA_MAX = enum.auto()

    # same as NEW_COUNT except that no actual new count is performed,
    # just displaying the status
    DISPLAY_STATUS = enum.auto()

    # drawing to select a candidate
    DRAW_SELECT = enum.auto()

    # a candidate is elected according to §19.1
    ELECT_19_1 = enum.auto()

    # a candidate was elected in an earlier election §21
    ELECTED_EARLIER = enum.auto()

    # calculation of election number for a regular round
    ELECTION_NUMBER = enum.auto()

    # calculation of election number for a substitute round
    ELECTION_NUMBER_SUBSTITUTE = enum.auto()

    # a candidate was excluded earlier
    EXCLUDED_EARLIER = enum.auto()

    # a candidate is member of a group that reached its max. value
    MAX_QUOTA_VALUE_EXCLUDED = enum.auto()

    # max-value for a quota group is reached
    MAX_QUOTA_VALUE_REACHED = enum.auto()

    # new count performed
    NEW_COUNT = enum.auto()

    # new regular round starts
    NEW_REGULAR_ROUND = enum.auto()

    # new substitute round starts
    NEW_SUBSTITUTE_ROUND = enum.auto()

    # no substitute candidates to be elected
    NO_ELECTABLE_SUBSTITUTES = enum.auto()

    # §21 within §16.3
    NO_EXCL_CANDIDATES_21 = enum.auto()

    # not enough unelected candidates for a substitute-round
    NOT_ENOUGH_FOR_SUBSTITUTE_ROUND = enum.auto()

    # empty quota group detected before the start of the of regular count
    QUOTA_GROUP_EMPTY = enum.auto()

    # the min_value_substitutes for a quota-group is adjusted
    QUOTA_MIN_VALUE_SUB_ADJUSTED = enum.auto()

    # at least one quota-group has min_value == 0
    QUOTA_MIN_VALUE_ZERO = enum.auto()

    # candidates <= regular candidates to be elected
    QUOTA_NOT_ENOUGH_CANDIDATES = enum.auto()

    # special case for OsloMet
    QUOTA_OSLOMET = enum.auto()

    # one of the gender groups is empty before starting a substitute count
    QUOTA_SUB_GROUP_EMPTY = enum.auto()

    # at least one of the gender groups has min_value_substitutes == 0
    QUOTA_SUB_MIN_VALUE_ZERO = enum.auto()

    # unelected candidates <= substitute candidates to be elected
    QUOTA_SUB_NOT_ENOUGH_CANDIDATES = enum.auto()

    # quota status for substitutes updated
    QUOTA_SUB_UPDATED = enum.auto()

    # candidates with the same score that can not be elected together
    SAME_SCORE = enum.auto()

    # candidates with the same surplus
    SAME_SURPLUS = enum.auto()

    # terminate election / count according to §19.1
    TERMINATE_19_1 = enum.auto()

    # terminate election / count according to §19.2
    TERMINATE_19_2 = enum.auto()

    # terminating regular count
    TERMINATE_REGULAR_COUNT = enum.auto()

    # terminates the entire count of regular candidates
    TERMINATE_SUBSTITUTE_COUNT = enum.auto()

    # terminates only the the election of the current substitute candidate
    TERMINATE_SUBSTITUTE_ELECTION = enum.auto()

    # transfer ballots from excluded candidates
    TRANSFER_BALLOTS_FROM_EXCL_CAND = enum.auto()

    # transfer excluded ballots to remaining candidates
    TRANSFER_EBALLOTS_TO_REMAINING_CAND = enum.auto()

    # transfers the ballots of an elected candidate
    TRANSFER_SURPLUS = enum.auto()

    # transferring ballots with certain weight
    TRANSFERRING_BALLOTS_WITH_WEIGHT = enum.auto()

    # unable to exclude any candidate in according to §16.3
    UNABLE_TO_EXCLUDE = enum.auto()

    # update surplus for elected candidate
    UPDATE_SURPLUS = enum.auto()


class CountingEvent:
    """
    The CountingEvent class

    Describes a single UiOSTV counting event like f.i. a count result.
    Counting-events are used when generating an election protocol
    """

    def __init__(self, event_type, event_data):
        """
        :param event_type: The type of event
        :type event_type: CountingEventType

        :param event_data: Relevant data for this type of event
        :type event_data: obj
        """
        self.event_type = str(event_type).split('.')[-1]
        self.event_data = event_data
        if (
                event_type is CountingEventType.NEW_COUNT or
                event_type is CountingEventType.DISPLAY_STATUS
        ):
            new_count_results = []
            for value in event_data['count_results']:
                # value[0] - candidate_obj
                # value[1] - count (decimal.Decimal)
                new_count_results.append(
                    tuple([str(value[0].id),
                           str(value[1])]))
            self.event_data['count_results'] = new_count_results
            # pick up the per pollbook stats
            if 'count_result_stats' in event_data:
                new_count_result_stats = {}
                for pbook, value in event_data['count_result_stats'].items():
                    pbook_id = str(pbook.id)
                    new_count_result_stats[pbook_id] = {}
                    new_count_result_stats[pbook_id]['total'] = str(
                        event_data['count_result_stats'][pbook]['total'])
                    for cand, items in value.items():
                        if cand == 'total':
                            # the pollbook total
                            continue
                        # regular candidate
                        cand_id = str(cand.id)
                        new_count_result_stats[pbook_id][
                            str(cand_id)] = {}
                        new_count_result_stats[pbook_id][
                            str(cand_id)]['total'] = str(items['total'])
                        new_count_result_stats[pbook_id][
                            str(cand_id)]['amount'] = str(items['amount'])
                        new_count_result_stats[pbook_id][
                            str(cand_id)]['percent_pollbook'] = str(
                                items['percent_pollbook'])
                self.event_data['count_result_stats'] = new_count_result_stats
            if 'count_result_stats_ntnu' in event_data:
                # pick up the NTNU-CV stats
                new_count_result_stats = {}
                for cand, val in event_data['count_result_stats_ntnu'].items():
                    cand_id = str(cand.id)
                    new_count_result_stats[cand_id] = []
                    for factor, amount in val.items():
                        new_count_result_stats[cand_id].append(
                            [factor, amount])
                self.event_data[
                    'count_result_stats_ntnu'] = new_count_result_stats

    def to_dict(self):
        """
        Returns a dict representation of the object

        :return: dict representation of the object
        :rtype: dict
        """
        return self.__dict__


class DrawingBranchState(enum.Enum):
    """DrawingBranch state types"""
    OPEN = 1  # never visited
    VISITED = 2  # currently visited
    CLOSED = 4  # closed


class DumpFormat(enum.Enum):
    """Dump format types"""
    EVALG2 = 1
    EVALG3 = 2


class DrawingBranch:
    """Represents a single branch in a DrawingNode"""

    def __init__(self, member, node):
        """
        :param member: Any member object
        :type member: object

        :param node: The DrawingNode object the branch belongs to
        :type node: DrawingNode
        """
        self._member = member
        self._node = node
        self._state = DrawingBranchState.OPEN

    @property
    def member(self):
        """member-property"""
        return self._member

    @property
    def state(self):
        """state-property"""
        return self._state

    @state.setter
    def state(self, value):
        """state-property setter"""
        self._state = value

    def __str__(self):
        return '<{member}>'.format(member=str(self._member))

    def close(self):
        """
        Marks the branch as CLOSED and propagates closure to node,
        node.parent etc.
        """
        self._state = DrawingBranchState.CLOSED
        if self._node.parent is None:  # root Node
            return
        if self._node.is_closed():
            # all branches of owner-node closed, close its parent
            self._node.parent.close()

    def get_branch_probability(self):
        """
        Returns the probability of this branch

        :return: The probability of this branch
        :rtype: decimal.Decimal
        """
        local_probability = (decimal.Decimal(1) /
                             decimal.Decimal(self._node.probability_factor))
        if self._node.parent is None:  # root Node
            return local_probability
        return local_probability * self._node.parent.get_branch_probability()


class DrawingNode:
    """Represents a node for drawing members (currently candidates)"""

    def __init__(self,
                 parent,
                 members,
                 test_mode=False,
                 interactive_drawing=False):
        """
        :param parent: The DrawingBranch that spawned this node (None == root)
        :type parent: DrawingBranch, None

        :param members: The members (branches) of this node
        :type members: collections.abc.Sequence

        :param test_mode: Generate the same (non-random) result by using
                          the same seed. (used for testing) (default: False)
        :type test_mode: bool

        :param interactive_drawing: Prompt the user when drawing
                                    (manual drawing) (default: False)
        :type interactive_drawing: bool
        """
        self._parent = parent
        # N.B. interactive_drawing is used for CLI and testing only
        self._interactive_drawing = interactive_drawing
        self._probability_factor = len(members)
        self._members = []
        for member in members:
            self._members.append(DrawingBranch(member, self))
        if test_mode:
            logger.warning("Using testing / non-random mode")
            self._rnd = random.SystemRandom(1)
        else:
            self._rnd = secrets.SystemRandom()

    @property
    def members(self):
        """members-property"""
        return tuple(self._members)

    @property
    def parent(self):
        """parent-property"""
        return self._parent

    @property
    def probability_factor(self):
        """probability_factor-property"""
        return self._probability_factor

    def __str__(self):
        return '{id}: {members}'.format(
            id=id(self),
            members=', '.join(map(lambda x: str(x), self._members)))

    def is_closed(self):
        """
        :return: True if there are no more open branches, False otherwise
        :rtype: bool
        """
        for member in self._members:
            if member.state != DrawingBranchState.CLOSED:
                return False
        return True

    def pick_branch(self):
        """
        Returns a drawing branch.

        If any of the branches has state VISITED, return it, if not - pick a
        random OPEN branch and set its state to VISITED.

        :return: Drawing branch
        :rtype: DrawingBranch
        """
        visited = self._get_visited_branch()
        if visited is not None:
            return visited
        open_branches = self._get_open_branches()
        if self._interactive_drawing:
            logger.warning("Interactive drawing")
            while True:
                idx_list = []
                for idx, open_branch in enumerate(open_branches, 1):
                    idx_list.append(idx)
                    print(f'{idx}: {open_branch.member}', flush=True)
                choice = int(input('Select members: ').strip())
                if choice not in idx_list:
                    print('Invalid choice', flush=True)
                    continue
                branch = open_branches[choice - 1]
                break
        else:
            branch = self._rnd.choice(open_branches)
        branch.state = DrawingBranchState.VISITED
        return branch

    def _get_open_branches(self):
        """Returns a tuple of open branches"""
        return tuple(filter(lambda b: b.state is DrawingBranchState.OPEN,
                            self._members))

    def _get_visited_branch(self):
        """Return the visited branch if any, None if no such branch"""
        for member in self._members:
            if member.state is DrawingBranchState.VISITED:
                return member
        return None


class ElectionCountTree:
    """
    The ElectionCountTree-class

    Election-path container
    """
    def __init__(self):
        """Creates an ElectionCountTree object"""
        self._election_path_dict = {}
        self._drawing = None

    @property
    def default_path(self):
        """default_path-property"""
        if not self._election_path_dict:
            return None
        return self.election_paths[0]

    @property
    def drawing(self):
        """drawing-property"""
        if self._drawing is None:
            return len(self._election_path_dict) > 1
        return self._drawing

    @drawing.setter
    def drawing(self, value):
        """drawing-property setter"""
        self._drawing = value

    @property
    def election_paths(self):
        """election_paths-property"""
        return tuple(self._election_path_dict.keys())

    def append_path(self, path):
        """
        Appends a ElectionCountPath-object.

        :param path: The ElectionCountPath-object
        :type path: ElectionCountPath
        """
        self._election_path_dict[path] = 1

    def get_results(self):
        """
        Returns all possible results ordered by probability

        :return: All results dict
        :rtype: dict
        """
        results_dict = {}
        for path in self._election_path_dict:
            total_results = tuple(path.get_elected_regular_candidates() +
                                  path.get_elected_substitute_candidates())
            if total_results not in results_dict:
                # first time
                results_dict[total_results] = {
                    'paths': 1,
                    'result_objects': [path.get_result()],
                    'regulars': path.get_elected_regular_candidates(),
                    'substitutes': path.get_elected_substitute_candidates(),
                    'probability': path.get_probability()}
                continue
            results_dict[total_results][
                'probability'] += path.get_probability()
            results_dict[total_results]['paths'] += 1
            results_dict[total_results]['result_objects'].append(
                path.get_result())
        return results_dict

    @staticmethod
    def order_results_by(results, key):
        """
        Returns a list of result dicts ordered by key.

        Currently key can be 'paths' and 'probability'

        :param key: The key to order by
        :type key: str

        :param results: tuple-key: result-dict dict
        :type results: dict

        :return: List of result dicts ordered by the given key
        :rtype: list
        """
        results_list = []
        results_counter = collections.Counter()
        for tkey, result_dict in results.items():
            results_counter[tkey] = result_dict[key]
        for tkey, _ in results_counter.most_common():
            results_list.append(results[tkey])
        return results_list

    def print_summary(self):
        """Prints the counting summary to logger.debug"""
        logger.debug("=" * 16)
        logger.debug("Summary:")
        logger.debug("Drawing: %s", 'yes' if self.drawing else 'no')
        for i, path in enumerate(self._election_path_dict.keys(), 1):
            logger.debug("-" * 8)
            logger.debug("Counting path %d (%s)", i, path.get_probability())
            regular_candidates = path.get_elected_regular_candidates()
            substitute_candidates = path.get_elected_substitute_candidates()
            if regular_candidates:
                logger.debug("Elected regular candidates:")
                for candidate in regular_candidates:
                    logger.debug(candidate)
            if substitute_candidates:
                logger.debug("Elected substitute candidates:")
                for j, candidate in enumerate(substitute_candidates, 1):
                    logger.debug("%d substitute: %s", j, candidate)


class ElectionCountPath:
    """
    The ElectionCountPath-class

    Represent a single election-path
    """

    def __init__(self):
        """Creates an ElectionCountPath object."""
        self._round_state_list = []
        self._current_drawing_branch = None

    @property
    def current_drawing_branch(self):
        """current_drawing_branch-property"""
        return self._current_drawing_branch

    @property
    def drawing(self):
        """drawing-property"""
        return self._current_drawing_branch is not None

    @current_drawing_branch.setter # type: ignore
    def current_drawing_branch(self, value):
        """current_drawing_branch-property setter"""
        self._current_drawing_branch = value

    def append_round_state(self, round_state):
        """Appends a RoundState object to the path."""
        self._round_state_list.append(round_state)

    def get_elected_regular_candidates(self):
        """
        :return: The elected regular candidates for this path
        :rtype: tuple
        """
        if not self._round_state_list:
            return tuple()
        last_state = self._round_state_list[-1]
        elected_substitutes = last_state.all_elected_substitutes
        return tuple([c for c in last_state.all_elected_candidates
                      if c not in elected_substitutes])

    def get_elected_substitute_candidates(self):
        """
        :return: The elected substitute candidates for this path
        :rtype: tuple
        """
        if not self._round_state_list:
            return tuple()
        last_state = self._round_state_list[-1]
        return last_state.all_elected_substitutes

    def get_poll_alternatives(self):
        """
        :return: The elected substitute candidates for this path
        :rtype: tuple
        """
        if not self._round_state_list:
            return dict()
        last_state = self._round_state_list[-1]
        return last_state.alternatives

    def get_probability(self):
        """
        :return: The probability of the patch
        :rtype: decimal.Decimal
        """
        if self._current_drawing_branch is None:
            return decimal.Decimal(1)
        if self._current_drawing_branch is True:
            # drawing, but no tree (NTNU)
            return decimal.Decimal(1)
        return self._current_drawing_branch.get_branch_probability()

    def get_result(self):
        """
        :return: The result-object for this path
        :rtype: base.Result
        """
        if not self._round_state_list or not self._round_state_list[-1].final:
            raise CountingFailure('Empty or unfinished path')
        counter_obj = self._round_state_list[-1].round_obj.counter_obj
        election = counter_obj.election
        meta = {
            'election_id': str(election.id),
            'election_name': election.name,
            'election_type': election.type_str,
            'drawing': self.drawing,
            'ballots_count': election.total_amount_ballots,
            'empty_ballots_count': election.total_amount_empty_ballots}
        pollbook_meta = []
        for pollbook in election.pollbooks:
            pollbook_meta.append(
                {'id': str(pollbook.id),
                 'ballots_count': pollbook.ballots_count,
                 'empty_ballots_count': pollbook.empty_ballots_count})
        meta['pollbooks'] = pollbook_meta
        if election.type_str == 'uio_stv':
            meta.update({
                'num_regular': election.num_choosable,
                'num_substitutes': election.num_substitutes,
            })
            return uiostv.Result(
                meta=meta,
                regular_candidates=[str(cand.id) for cand in
                                    self.get_elected_regular_candidates()],
                substitute_candidates=[
                    str(cand.id) for cand in
                    self.get_elected_substitute_candidates()])
        if election.type_str == 'uio_mv':
            return uiomv.Result(
                meta=meta,
                regular_candidates=[str(cand.id) for cand in
                                    self.get_elected_regular_candidates()])
        if election.type_str == 'ntnu_cv':
            return ntnucv.Result(
                meta=meta,
                regular_candidates=[str(cand.id) for cand in
                                    self.get_elected_regular_candidates()],
                substitute_candidates=[
                    str(cand.id) for cand in
                    self.get_elected_substitute_candidates()])
        if election.type_str == 'poll':
            return poll.Result(
                meta=meta,
                alternatives=self.get_poll_alternatives()
            )
        if election.type_str == 'mntv':
            logger.info(self.get_elected_regular_candidates())
            a = mntv.Result(
                meta=meta,
                regular_candidates=[str(cand.id) for cand in
                                    self.get_elected_regular_candidates()],
                substitute_candidates=[
                    str(cand.id) for cand in
                    self.get_elected_substitute_candidates()])
            logger.info(a)
            return a

        return None

    def get_protocol(self):
        """
        :return: The protocol-object for this path
        :rtype: base.Protocol
        """
        if not self._round_state_list or not self._round_state_list[-1].final:
            raise CountingFailure('Empty or unfinished path')
        counter_obj = self._round_state_list[-1].round_obj.counter_obj
        election = counter_obj.election
        candidates = {}
        for candidate in election.candidates:
            candidates.update({str(candidate.id): candidate.name})
        meta = {
            'election_id': str(election.id),
            'election_name': election.name,
            'election_type': election.type_str,
            'candidate_ids': [str(cand.id) for cand in election.candidates],
            'candidates': candidates,
            'counted_at': datetime.datetime.now().astimezone(
                pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S'),
            'counted_by': None,
            'election_start': election.start.astimezone(
                pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S'),
            'election_end': election.end.astimezone(
                pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S'),
            'drawing': self.drawing,
            'ballots_count': election.total_amount_ballots,
            'counting_ballots_count': election.total_amount_counting_ballots,
            'regular_candidate_ids': [
                str(cand.id) for cand in
                self.get_elected_regular_candidates()],
            'substitute_candidate_ids': [
                str(cand.id) for cand in
                self.get_elected_substitute_candidates()],
            'empty_ballots_count': election.total_amount_empty_ballots}
        pollbook_meta = []
        pollbook_mappings = {}
        for pollbook in election.pollbooks:
            pollbook_mappings.update({str(pollbook.id): pollbook.name})
            if 'scale_factor' not in meta:
                if hasattr(pollbook, 'scale_factor'):
                    meta['scale_factor'] = str(pollbook.scale_factor.quantize(
                        decimal.Decimal('1.00'),
                        decimal.ROUND_HALF_EVEN))
                else:
                    meta['scale_factor'] = '1'
            pollbook_meta.append(
                {'id': str(pollbook.id),
                 'name': pollbook.name,
                 'ballots_count': pollbook.ballots_count,
                 'counting_ballots_count': pollbook.counting_ballots_count,
                 'empty_ballots_count': pollbook.empty_ballots_count,
                 'weight': pollbook.weight,
                 'weight_per_vote': str(pollbook.weight_per_vote),
                 'weight_per_pollbook': str(pollbook.weight_per_pollbook)})
        meta['pollbook_mappings'] = pollbook_mappings
        meta['pollbooks'] = pollbook_meta
        quota_meta = []
        for quota in counter_obj.quotas:
            logger.debug("Quota %s in protocol: %s",
                         quota.name,
                         str(id(quota)))
            quota_meta.append(
                {'name': quota.name,
                 'members': [str(member.id) for member in quota.members],
                 'min_value': quota.min_value,
                 'max_value_regular': counter_obj.max_choosable(quota)})
        meta['quotas'] = quota_meta
        rounds = []
        for state in self._round_state_list:
            rounds.append(state.events)
        if election.type_str == 'uio_stv':
            meta.update({
                'num_regular': election.num_choosable,
                'num_substitutes': election.num_substitutes,
            })
            return uiostv.Protocol(meta=meta, rounds=rounds)
        if election.type_str == 'uio_mv':
            return uiomv.Protocol(meta=meta, rounds=rounds)
        if election.type_str == 'ntnu_cv':
            return ntnucv.Protocol(meta=meta, rounds=rounds)
        if election.type_str == 'poll':
            return poll.Protocol(meta=meta, rounds=rounds)
        if election.type_str == 'mntv':
            return mntv.Protocol(meta=meta, rounds=rounds)
        return None


class Counter:
    """
    The Counter class

    This class should be agnostic to counting method(s).
    """

    def __init__(self, election, ballots, **kwargs):
        """
        :param election: The Election object
        :type election: object

        :param ballots: The sequence of ballots
        :type ballots: collections.abc.Sequence

        Keyword-arguments:
        :param alternative_paths: In case of drawing, generate alt. paths
        :type alternative_paths: bool

        :param test_mode: In case of drawing, generate the same (non-random)
                          "random result(s) (default: False)"
        :type test_mode: bool

        :param interactive_drawing: Prompt the user when drawing
                                    (manual drawing) (default: False)
        :type interactive_drawing: bool

        :param regular_count_only: Perform only the regular count
                                   (default: False)
        :type regular_count_only: bool
        """
        if not isinstance(ballots, collections.abc.Sequence):
            raise TypeError(
                'ballots must be if the type collections.abc.Sequence')
        self._election_obj = election
        self._ballots = tuple(ballots)
        # having a local copy of quotas is essential
        # evalg.models.election.Election.quotas will always return a new set
        # of QuotaGroup objects
        self._quotas = election.quotas
        self._drawing_nodes = []
        # kwargs:
        self._alternative_paths = kwargs.get('alternative_paths', False)
        self._test_mode = kwargs.get('test_mode', False)
        # N.B. interactive_drawing is used for CLI and testing only
        self._interactive_drawing = kwargs.get('interactive_drawing', False)
        self._regular_count_only = kwargs.get('regular_count_only', False)

        self._current_election_path = None
        self._counting_ballots = tuple([ballot for ballot in self._ballots if
                                        ballot.candidates])
        logger.info("Total number of ballots: %d",
                    self._election_obj.total_amount_ballots)
        logger.debug("Total number of ballots (debug): %d",
                     len(self._ballots))
        logger.info("Total number of blank votes: %d",
                    self._election_obj.total_amount_empty_ballots)
        logger.info("Total number of counting votes: %d",
                    self._election_obj.total_amount_counting_ballots)
        for pollbook in self._election_obj.pollbooks:
            logger.info("Number of ballots from %s: %d",
                        pollbook.name,
                        pollbook.ballots_count)
            logger.info("Blank votes from %s: %d",
                        pollbook.name,
                        pollbook.empty_ballots_count)
            logger.info("Counting votes from %s: %d",
                        pollbook.name,
                        pollbook.counting_ballots_count)
            logger.info("Pollbook %s has weight per vote: %s",
                        pollbook,
                        pollbook.weight_per_vote)
            logger.info("Pollbook %s has (adjusted) weight per vote: %s",
                        pollbook,
                        pollbook.weight_per_pollbook)
        if not self._quotas:
            logger.info("No quota groups defined")
        for quota in self._quotas:
            logger.info("Quota group %s defined with min_value=%d and "
                        "implicit max_value=%d for regular candidates",
                        quota.name,
                        quota.min_value,
                        self.max_choosable(quota))
            logger.info("Quota group %s defined with min_value_substitutes=%d "
                        "and implicit max_value=%d for substitute candidates",
                        quota.name,
                        quota.min_value_substitutes,
                        self.max_substitutes(quota))

    @property
    def ballots(self):
        """ballots-property"""
        return self._ballots

    @property
    def candidates(self):
        """candidates-property"""
        return self._election_obj.candidates

    @property
    def counting_ballots(self):
        """counting_ballots-property"""
        return self._counting_ballots

    @property
    def election(self):
        """election-property"""
        return self._election_obj

    @property
    def quotas(self):
        """quotas-property"""
        return self._quotas

    @property
    def regular_count_only(self):
        """regular_count_only-property"""
        return self._regular_count_only

    def append_state_to_current_path(self, state):
        """
        Appends a RoundState object to the current path

        :param state: The round-state object
        :type state: object
        """
        self._current_election_path.append_round_state(state)

    def count(self):
        """
        The main machinery producing election-count trees.

        :return: The election-count tree
        :rtype: ElectionCountTree
        """
        election_count_tree = ElectionCountTree()
        self._current_election_path = ElectionCountPath()
        election_count_tree.append_path(self._current_election_path)
        # Now check election type and select the proper counting class
        # This method (and class) should remain algorithm agnostic.
        if self._election_obj.type_str not in RESULT_MAPPINGS.keys():
            # no other election algorithms implemented so far
            logger.warning("No algorithm implemented for election type: %s",
                           self._election_obj.type_str)
            return election_count_tree
        if self._election_obj.type_str == 'uio_stv':
            if self._election_obj.num_choosable > 0:
                round_cls = uiostv.RegularRound
            else:
                round_cls = uiostv.SubstituteRound
        elif self._election_obj.type_str == 'uio_mv':
            round_cls = uiomv.Round
        elif self._election_obj.type_str == 'ntnu_cv':
            round_cls = ntnucv.Round
        elif self._election_obj.type_str == 'poll':
            round_cls = poll.Round
        elif self._election_obj.type_str == 'mntv':
            round_cls = mntv.Round
        election_round = round_cls(self)
        election_round.count()
        if self._drawing_nodes:
            # there has been at least one drawing
            self._current_election_path.current_drawing_branch.close()
            if not self._alternative_paths:
                # No need to run through all election paths
                election_count_tree.drawing = True
                return election_count_tree
            root_drawing_node = self._drawing_nodes[0]
            while not root_drawing_node.is_closed():
                self._current_election_path = ElectionCountPath()  # new path
                election_count_tree.append_path(
                    self._current_election_path)
                new_round = round_cls(self)
                new_round.count()
                self._current_election_path.current_drawing_branch.close()
        return election_count_tree

    def draw_candidate(self, candidates):
        """
        Draws a candidate for the given round.

        This implements a type of caching in order to use properly
        the DrawingNode object(s)

        :param candidates: The candidates to choose from
        :type candidates: collections.abc.Sequence

        :return: The drawn candidate
        :rtype: object
        """
        if not self._drawing_nodes:
            # first draw
            node = DrawingNode(
                self._current_election_path.current_drawing_branch,
                tuple(candidates),
                test_mode=self._test_mode,
                interactive_drawing=self._interactive_drawing)
            self._drawing_nodes.append(node)  # the root node is always [0]
        else:
            for drawing_node in self._drawing_nodes:
                # node.parent is None => root node
                if (
                        drawing_node.parent is
                        self._current_election_path.current_drawing_branch
                ):
                    node = drawing_node
                    break
            else:
                # the branch doesn't own a node (bottom branch)
                node = DrawingNode(
                    self._current_election_path.current_drawing_branch,
                    tuple(candidates),
                    test_mode=self._test_mode,
                    interactive_drawing=self._interactive_drawing)
                self._drawing_nodes.append(node)
        branch = node.pick_branch()
        self._current_election_path.current_drawing_branch = branch
        return branch.member

    def dump(self, file_obj, dump_format=DumpFormat.EVALG2):
        """
        dumps the raw ballot respresentation

        :param file_obj: a file-like object
        :type file_obj: a file-like object

        :param dump_format: Dump format (default: DumpFormat.EVALG2)
        :type dump_format: DumpFormat
        """
        # using dumps will kill performance advantages
        if not isinstance(dump_format, DumpFormat):
            raise TypeError('dump_format must be a DumpFormat')
        if dump_format is not DumpFormat.EVALG2:
            raise NotImplementedError
        # assume DumpFormat.EVALG2 for now
        for ballot in sorted(self._ballots, key=lambda x: x.raw_string):
            file_obj.write((ballot.get_raw_string() + os.linesep).encode(
                'utf-8'))

    def dumps(self, dump_format=DumpFormat.EVALG2):
        """
        dumps the raw ballot respresentation

        :param dump_format: Dump format (default: DumpFormat.EVALG2)
        :type dump_format: DumpFormat

        :return: a string
        :rtype: str
        """
        if not isinstance(dump_format, DumpFormat):
            raise TypeError('dump_format must be a DumpFormat')
        if dump_format is not DumpFormat.EVALG2:
            raise NotImplementedError
        output = ''
        for ballot in sorted(self._ballots, key=lambda x: x.raw_string):
            output += ballot.raw_string + os.linesep
        return output

    def max_choosable(self, quota):
        """
        Returns the maximum about of choosable candidates for `quota`

        :param quota: The quota-object
        :type quota: object

        :return: The max. amount of choosable candidates from `quota`
        :rtype: int
        """
        other_quotas = [q for q in self._quotas if q != quota]
        max_choosable = (self._election_obj.num_choosable -
                         sum(map(operator.attrgetter('min_value'),
                                 other_quotas)))
        if max_choosable < 0:
            # Should not happen if the election is set properly. Raise?
            return 0
        return max_choosable

    def max_substitutes(self, quota):
        """
        Returns the maximum amount of substitute candidates for `quota`

        :param quota: The quota-object
        :type quota: object

        :return: The max. amount of substitute candidates from `quota`
        :rtype: int
        """
        other_quotas = [q for q in self._quotas if q != quota]
        max_substitutes = (self._election_obj.num_substitutes -
                           sum(map(operator.attrgetter(
                               'min_value_substitutes'),
                                   other_quotas)))
        if max_substitutes < 0:
            # Should not happen if the election is set properly. Raise?
            return 0
        return max_substitutes

    def shuffle_candidates(self, candidates):
        """
        Shuffles the any muntable sequence with random.shuffle *in place*
        This should be used *only* by counting algorithms that do not keep
        real election trees

        :param candidates: The candidates list
        :type candidates: list
        """
        if self._test_mode:
            rnd = random.SystemRandom(0)
        else:
            rnd = random.SystemRandom()
        rnd.shuffle(candidates)
        # hack that marks the current (and only) election path as "drawing"
        self._current_election_path.current_drawing_branch = True
