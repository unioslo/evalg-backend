# -*- coding: utf-8 -*-
"""Standalone classes for handleing evalg 3 count (.json) files"""
import collections
import datetime
import decimal
import enum
import io
import json
import logging
import math

SEX_MALE = 0
SEX_FEMALE = 1

DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class InvalidBallotException(Exception):
    """Raised if invalid ballot is detected"""
    pass


class InvalidFileException(Exception):
    """Raised if input file seems to be invalid"""
    pass


class EvalgSex(enum.Enum):
    """Sex enum"""
    MALE = 1
    FEMALE = 2


class Pollbook:
    """The pollbook-class"""

    def __init__(self, pollbook_id, pollbook_name, weight):
        """
        :param pollbook_id: The defined id
        :type pollbook_id: str

        :param pollbook_name: The defined name
        :type pollbook_name: str

        :param weight: The defined weight
        :type weight: decimal.Decimal
        """
        self._pollbook_id = pollbook_id
        self._name = pollbook_name
        self._weight = weight
        self._ballots_cnt = 0
        self._empty_ballots_cnt = 0
        self._weight_per_pollbook = decimal.Decimal('1.00')

    @property
    def pollbook_id(self):
        """pollbook_id-property"""
        return self._pollbook_id

    @property
    def ballots_count(self):
        """ballots_count-property"""
        return self._ballots_cnt

    @ballots_count.setter
    def ballots_count(self, value):
        """ballots_count-property setter"""
        self._ballots_cnt = value

    @property
    def counting_ballots_count(self):
        """ballots_count-property"""
        return self._ballots_cnt - self._empty_ballots_cnt

    @property
    def empty_ballots_count(self):
        """empty_ballots_count-property"""
        return self._empty_ballots_cnt

    @empty_ballots_count.setter
    def empty_ballots_count(self, value):
        """empty_ballots_count-property setter"""
        self._empty_ballots_cnt = value

    @property
    def id(self):
        """id-property"""
        return self._pollbook_id

    @property
    def name(self):
        """name-property"""
        return self._name

    @property
    def scale_factor(self):
        """scale_factor-property"""
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, value):
        """scale_factor-property setter"""
        self._scale_factor = value

    @property
    def weight(self):
        """weight-property"""
        return self._weight

    @property
    def weight_per_pollbook(self):
        """weight_per_pollbook-property"""
        return self._weight_per_pollbook

    @property
    def weight_per_vote(self):
        """weight_per_vote-property"""
        if not self._ballots_cnt - self._empty_ballots_cnt:
            # no (real) ballots related to this pollbook
            # avoid devision by 0
            return decimal.Decimal('0')
        return self._weight / decimal.Decimal(
            self._ballots_cnt - self._empty_ballots_cnt)

    def __str__(self):
        return '{id}: {name} ({weight})'.format(id=self._pollbook_id,
                                                name=self._name,
                                                weight=self._weight)

    def set_weight_per_pollbook(self, value):
        """
        Calculates and sets own weight_per_pollbook based on the
        smallest (1.0) index weight per vote
        IV §32
        """
        if not value:  # avoid devision by 0
            # paranoia: should not happen because of client check
            self._weight_per_pollbook = decimal.Decimal(0)
        else:
            self._weight_per_pollbook = self.weight_per_vote / value


class Candidate:
    """The candidate-class"""

    def __init__(self, candidate_id, candidate_name, sex=None):
        """
        :param candidate_id: candidate-id
        :type candidate_id: int, str

        :param candidate_name: candidate-name
        :type candidate_name: str

        :param sex: Sex (or None)
        :type sex: evalg.counting.standalone.EvalgSex
        """
        self._candidate_id = candidate_id
        self._name = candidate_name
        self._sex = sex

    @property
    def candidate_id(self):
        """candidate_id-property"""
        return self._candidate_id

    @property
    def id(self):
        """candidate_id-property"""
        return self._candidate_id

    @property
    def name(self):
        """name-property"""
        return self._name

    def __str__(self):
        if self._sex is None:
            return '{id} - {name}'.format(
                id=self._candidate_id,
                name=self._name)
        return '{id} - {name} ({sex})'.format(
            id=self._candidate_id,
            name=self._name,
            sex='F' if self._sex == EvalgSex.FEMALE else 'M')


class Quota:
    """The quota-class"""

    def __init__(self,
                 quota_name,
                 members_list,
                 min_value,
                 min_value_substitutes):
        """
        :param quota_name: The quota-name
        :type quota_name: str or dict

        :param members_list: The sequence of candidates
        :type members_list: collections.abc.Sequence

        :param min_value: The min value set for this quota group
        :type min_value: int

        :param min_value_substitutes: The min value set for this quota group
        :type min_value_substitutes: int
        """
        self._name = quota_name
        self._members_list = tuple(members_list)
        self._min_value = min_value
        self._min_value_substitutes = min_value_substitutes

    @property
    def members(self):
        """members-property"""
        return self._members_list

    @property
    def name(self):
        """name-property"""
        return self._name

    @property
    def min_value(self):
        """min_value-property"""
        return self._min_value

    @property
    def min_value_substitutes(self):
        """min_value_substitutes-property"""
        return self._min_value_substitutes

    @min_value_substitutes.setter
    def min_value_substitutes(self, value):
        """min_value_substitutes-property setter"""
        self._min_value_substitutes = value

    def __str__(self):
        return '{name}: {members}'.format(
            name=self._name,
            members=', '.join(map(lambda x: str(x), self._members_list)))


class Ballot:
    """The ballot-class"""

    def __init__(self, pollbook, candidates_list):
        """
        :param pollbook: The pollbook the ballot bellongs to
        :type pollbook: EvalgLegacyPollbook

        :param candidates_list: The (ordered) sequence of candidates
        :type candidates_list: collections.abc.Sequence
        """
        if not isinstance(candidates_list, collections.abc.Sequence):
            raise TypeError(
                'candidates_list must be if the type collections.abc.Sequence')
        self._pollbook_obj = pollbook
        self._candidates_list = list(candidates_list)
        self._raw_string = None
        self._pollbook_obj.ballots_count += 1
        if not self._candidates_list:  # empty ballot
            self._pollbook_obj.empty_ballots_count += 1

    @property
    def candidates(self):
        """candidates-property"""
        return self._candidates_list

    @property
    def raw_string(self):
        """
        A string based on voters_lists_id and candidates
        to be used for sorting / raw representation ballots
        """
        if self._raw_string is None:
            self._raw_string = ' '.join(
                [self._pollbook_obj.pollbook_id] +
                [candidate.candidate_id for candidate in
                 self._candidates_list])
        return self._raw_string

    @property
    def pollbook(self):
        """pollbook-property"""
        return self._pollbook_obj

    def __str__(self):
        return '{pollbook}: {votes}'.format(
            pollbook=self._pollbook_obj,
            votes=' -> '.join([str(cand) for cand in self._candidates_list]))


class Election:
    """The election-class"""

    def __init__(self, election_file):
        """
        :param election_file: The election / ballot (.json) file
        :type election_file: str
        """
        self._election_id = None
        self._name = 'Standalone election'
        self._num_choosable = -1
        self._num_substitutes = -1
        self._candidates_list = []
        self._candidates_dict = {}  # implements id -> candidate "caching"
        self._pollbook_dict = {}
        self._voters_lists_dict = {}  # 'ballot_id': cansus_obj dict
        self._ballot_list = []
        self._quota_list = []
        self._election_type = None
        self._end = None
        self._start = None

        with io.open(election_file, 'r', encoding='utf-8') as json_file:
            try:
                self._json_dict = json.load(json_file)
            except json.JSONDecodeError:
                raise InvalidFileException
        if 'meta' in self._json_dict:
            self._election_id = self._json_dict['meta'].get('electionId',
                                                            'electionId')
            self._name = self._json_dict['meta'].get('electionName',
                                                     'electionName')
            if isinstance(self._name, dict):
                self._name = self._name['en']
            self._election_type = self._json_dict['meta'].get('electionType',
                                                              'uio_stv')
            self._num_choosable = self._json_dict['meta'].get('numRegular',
                                                              0)
            self._num_substitutes = self._json_dict['meta'].get(
                'numSubstitutes',
                0)
            self._start = self._json_dict['meta'].get('start')
            if not self._start:
                self._start = datetime.datetime.now()
            else:
                self._start = datetime.datetime.fromisoformat(self._start)
            self._end = self._json_dict['meta'].get('end')
            if not self._end:
                self._end = datetime.datetime.now()
            else:
                self._end = datetime.datetime.fromisoformat(self._end)
        if 'candidateNames' not in self._json_dict:
            raise Exception('Missing candidates')
        for candidate_id, name in self._json_dict['candidateNames'].items():
            candidate = Candidate(candidate_id, name)
            self._candidates_list.append(candidate)
            logger.info("Adding candidate: %s", candidate)
        for pollbook_id, name in self._json_dict['pollbookNames'].items():
            pollbook = Pollbook(pollbook_id, name['en'], decimal.Decimal(1))
            self._pollbook_dict[pollbook_id] = pollbook
            logger.info("Adding pollbook: %s", pollbook)
        if 'quotas' in self._json_dict:
            for quota_group in self._json_dict['quotas']:
                members = [self._get_candidate_by_id(c_id) for c_id in
                           quota_group['members']]
                if self._num_choosable <= 1:
                    min_value = 0
                elif self._num_choosable <= 3:
                    min_value = 1
                elif self._num_choosable:
                    min_value = math.ceil(0.4 * self._num_choosable)
                if self._num_substitutes <= 1:
                    min_value_substitutes = 0
                elif self._num_substitutes <= 3:
                    min_value_substitutes = 1
                elif self._num_substitutes:
                    min_value_substitutes = math.ceil(
                        0.4 * self.num_substitutes)
                min_value = min([min_value, len(members)])
                min_value_substitutes = min([min_value_substitutes,
                                             len(members) - min_value])
                quota = Quota(quota_group['name'],
                              members,
                              min_value,
                              min_value_substitutes)
                self._quota_list.append(quota)
                logger.info("Adding quota group: %s", quota)
        for ballot_dict in self._json_dict['ballots']:
            try:
                ballot = Ballot(self._pollbook_dict[ballot_dict['pollbookId']],
                                [self._get_candidate_by_id(c_id) for c_id in
                                 ballot_dict['rankedCandidateIds']])
            except KeyError:
                raise InvalidBallotException
            self._ballot_list.append(ballot)
            # logger.debug("Adding ballot: %s", ballot)
        pollbook_list = self._pollbook_dict.values()
        min_wpv = min([pollbook.weight_per_vote for
                       pollbook in pollbook_list if pollbook.weight_per_vote],
                      default=decimal.Decimal(1))
        # scale_factor is calculated only once in order to avoid round off
        # discrepancies.
        # scale_factor is only used for the protocol generation
        scale_factor = decimal.Decimal(1) / min_wpv
        for pollbook in pollbook_list:
            pollbook.set_weight_per_pollbook(min_wpv)
            pollbook.scale_factor = scale_factor

    @property
    def ballots(self):
        """
        ballots property
        """
        return tuple(self._ballot_list)

    @property
    def candidates(self):
        """
        candidates property
        """
        return tuple(self._candidates_list)

    @property
    def end(self):
        """end-property"""
        return self._end

    @property
    def pollbooks(self):
        """
        pollbooks-property
        """
        return self._pollbook_dict.values()

    @property
    def type(self):
        """
        type-property
        """
        return self._election_type

    @property
    def type_str(self):
        """
        type-property
        """
        return self._election_type

    @property
    def election_id(self):
        """
        election_id-property
        """
        return self._election_id

    @property
    def id(self):
        """election_id-property"""
        return self._election_id

    @property
    def name(self):
        """
        name-property
        """
        return self._name

    @property
    def num_choosable(self):
        """
        num_choosable-property
        """
        return self._num_choosable

    @property
    def num_substitutes(self):
        """
        num_substitutes-property
        """
        return self._num_substitutes

    @property
    def quotas(self):
        """
        quotas-property
        """
        return tuple(self._quota_list)

    @property
    def start(self):
        """start-property"""
        return self._start

    @property
    def total_amount_empty_ballots(self):
        """
        ballots property
        """
        return sum(
            [c.empty_ballots_count for c in self._pollbook_dict.values()])

    @property
    def total_amount_ballots(self):
        """
        total_amount_ballots-property
        """
        return sum([c.ballots_count for c in self._pollbook_dict.values()])

    @property
    def total_amount_counting_ballots(self):
        """
        total_amount_counting_ballots-property
        """
        return sum(
            [c.counting_ballots_count for c in self._pollbook_dict.values()])

    @property
    def voters_lists(self):
        """
        voters_lists-property
        """
        return self._voters_lists_dict

    def __str__(self):
        return ('{id} - {name} - {election_type} - '
                '{num_choosable},{num_substitutes}'.format(
                    id=self._election_id,
                    name=self._name,
                    election_type=self._election_type,
                    num_choosable=self._num_choosable,
                    num_substitutes=self._num_substitutes))

    def _get_candidate_by_id(self, candidate_id):
        """
        Finds a candidate based on candidate-id.
        :param candidate_id: Candidate-id
        :type candidate_id: str

        :return: candidate
        :rtype: evalg.counting.standalone.Candidate
        """
        if candidate_id in self._candidates_dict:
            return self._candidates_dict[candidate_id]
        for candidate in self._candidates_list:
            if candidate_id == candidate.candidate_id:
                self._candidates_dict[candidate_id] = candidate
                return candidate
        raise Exception('No candidate with id={id} found'.format(
            id=candidate_id))
