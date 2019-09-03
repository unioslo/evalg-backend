# -*- coding: utf-8 -*-
"""Legacy classes for handleing eValg 2 count (.zip) files"""
import collections
import datetime
import decimal
import enum
import logging
import math
import os
import xml.etree.ElementTree as ET
import zipfile


EVALG_LEGACY_INFO_FILE = 'electionInfo.xml'
EVALG_LEGACY_VOTERS_LIST_ID_FILE = 'voteId2VotersListId.dat'

SEX_MALE = 0
SEX_FEMALE = 1

DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class EvalgLegacyInvalidBallot(Exception):
    """Raised if invalid ballot is detected"""
    pass


class EvalgLegacyInvalidFile(Exception):
    """Raised if input file seems to be invalid"""
    pass


class EvalgSex(enum.Enum):
    """Sex enum"""
    MALE = 1
    FEMALE = 2


class EvalgLegacyPollbook:
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


class EvalgLegacyCandidate:
    """The candidate-class"""

    def __init__(self, candidate_id, candidate_name, pid):
        """
        :param candidate_id: candidate-id
        :type candidate_id: int, str

        :param candidate_name: candidate-name
        :type candidate_name: str

        :param pid: candidate-sex
        :type pid: str
        """
        self._candidate_id = candidate_id
        self._name = candidate_name
        self._pid = pid
        self._sex = self.fnr_to_sex(pid)

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

    @property
    def pid(self):
        """pid-property"""
        return self._pid

    def __str__(self):
        return '{id} - {name} ({sex})'.format(
            id=self._candidate_id,
            name=self._name,
            sex='F' if self._sex == EvalgSex.FEMALE else 'M')

    @staticmethod
    def fnr_to_sex(fnr):
        """
        https://no.wikipedia.org/wiki/F%C3%B8dselsnummer
        :param fnr: fodselsnummer
        :type fnr: str

        :return: the corresponding sex
        :rtype: EvalgSex
        """
        if not len(fnr) == 11:  # good idea?
            raise EvalgLegacyInvalidFile('Invalid fnr')
        if int(fnr[8]) % 2:  # odd number
            return EvalgSex.MALE
        return EvalgSex.FEMALE


class EvalgLegacyQuota:
    """The quota-class"""

    def __init__(self,
                 quota_id,
                 quota_name,
                 members_list,
                 min_value,
                 min_value_substitutes):
        """
        :param quota_id: The quota-id
        :type quota_id: str

        :param quota_name: The quota-name
        :type quota_name: str

        :param members_list: The sequence of candidates
        :type members_list: collections.abc.Sequence

        :param min_value: The min value set for this quota group
        :type min_value: int

        :param min_value_substitutes: The min value set for this quota group
        :type min_value_substitutes: int
        """
        self._quota_id = quota_id
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


class EvalgLegacyBallot:
    """The ballot-class"""

    def __init__(self, ballot_id, pollbook, candidates_list):
        """
        :param ballot_id: The ballot-id
        :type bellot_id: str

        :param pollbook: The pollbook the ballot bellongs to
        :type pollbook: EvalgLegacyPollbook

        :param candidates_list: The (ordered) sequence of candidates
        :type candidates_list: collections.abc.Sequence
        """
        if not isinstance(candidates_list, collections.abc.Sequence):
            raise TypeError(
                'candidates_list must be if the type collections.abc.Sequence')
        self._ballot_id = ballot_id
        self._pollbook_obj = pollbook
        self._candidates_list = list(candidates_list)
        self._raw_string = None
        self._pollbook_obj.ballots_count += 1
        if not self._candidates_list:  # empty ballot
            self._pollbook_obj.empty_ballots_count += 1

    @property
    def ballot_id(self):
        """id-property"""
        return self._ballot_id

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
        return '{ballot_id}/({pollbook}): {votes}'.format(
            ballot_id=self._ballot_id,
            pollbook=self._pollbook_obj,
            votes=' -> '.join([str(cand) for cand in self._candidates_list]))


class EvalgLegacyElection:
    """The election-class"""

    def __init__(self, legacy_election_file):
        """
        """
        self._election_id = None
        self._name = 'Legacy election'
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
        if not zipfile.is_zipfile(legacy_election_file):
            raise EvalgLegacyInvalidFile('Missing or invalid election-file')
        with zipfile.ZipFile(legacy_election_file) as zfile:
            with zfile.open(EVALG_LEGACY_INFO_FILE) as fp:
                self._fetch_election_data(fp)
            with zfile.open(EVALG_LEGACY_VOTERS_LIST_ID_FILE) as fp:
                self._fetch_voters_lists(fp)
            for ballot_file in zfile.namelist():
                if (
                        not ballot_file.lower().endswith('.xml') or
                        ballot_file == EVALG_LEGACY_INFO_FILE
                ):
                    continue
                with zfile.open(ballot_file) as fp:
                    self._add_ballot_from_file(fp)
        # set weight per pollbook
        pollbook_list = self._pollbook_dict.values()
        min_wpv = min([pollbook.weight_per_vote for
                       pollbook in pollbook_list if pollbook.weight_per_vote],
                      default=decimal.Decimal(1))
        for pollbook in pollbook_list:
            pollbook.set_weight_per_pollbook(min_wpv)

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

    def _fetch_election_data(self, xml_file_fp):
        """Loads election, candidate, pollbook and quota metadata"""
        tree = ET.parse(xml_file_fp)
        election_elem = tree.getroot()
        self._election_id = election_elem.attrib.get('id')
        self._name = election_elem.attrib.get('name')
        self._num_choosable = int(election_elem.attrib.get('num_chooseable'))
        num_substitutes = int(election_elem.attrib.get('num_substitutes'))
        if num_substitutes > -1:
            # num substitutes is explicit defined in eValg2
            self._num_substitutes = num_substitutes
        else:
            # -1 (and lower "illegal" values).
            # Set defaults based on num_choosable!
            if self._num_choosable == 1:
                self._num_substitutes = 2
            else:
                self._num_substitutes = self._num_choosable
        self._election_type = election_elem.attrib.get('election_type')
        self._start = datetime.datetime.fromisoformat(
            election_elem.attrib.get('start'))
        self._end = datetime.datetime.fromisoformat(
            election_elem.attrib.get('end'))
        for child in election_elem:
            if child.tag.lower() == 'candidate':
                candidate = EvalgLegacyCandidate(
                    child.attrib.get('id'),
                    '{} {}'.format(child.attrib.get('first_name'),
                                   child.attrib.get('last_name')),
                    child.attrib.get('pid'))
                self._candidates_list.append(candidate)
                logger.info("Adding candidate: %s", candidate)
            elif child.tag.lower() == 'census':
                self._pollbook_dict[child.attrib.get('id')] = (
                    EvalgLegacyPollbook(
                        child.attrib.get('id'),
                        child.attrib.get('name'),
                        decimal.Decimal(child.attrib.get('weight'))))
                logger.info("Adding pollbook: %s",
                            self._pollbook_dict[child.attrib.get('id')])
        # quota
        # Be paranoid and do not assume that the quota node is at the end of
        # the election_elem. Start new iteration.
        for child in election_elem:
            if child.tag.lower() == 'quota':
                qid = child.attrib.get('id')
                qname = child.attrib.get('name')
                members = []
                for member in child.findall('member'):
                    members.append(
                        self._get_candidate_by_pid(member.attrib.get('pid')))
                # assume stv election and gender quotas for now...
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
                quota = EvalgLegacyQuota(qid,
                                         qname,
                                         members,
                                         min_value,
                                         min_value_substitutes)
                self._quota_list.append(quota)
                logger.info("Adding quota group: %s", quota)

    def _get_candidate_by_id(self, candidate_id):
        """
        Finds a candidate based on candidate-id.
        :param candidate_id: Candidate-id
        :type candidate_id: str

        :return: candidate
        :rtype: EvalgLegacyCandidate
        """
        if candidate_id in self._candidates_dict:
            return self._candidates_dict[candidate_id]
        for candidate in self._candidates_list:
            if candidate_id == candidate.candidate_id:
                self._candidates_dict[candidate_id] = candidate
                return candidate
        raise Exception('No candidate with id={id} found'.format(
            id=candidate_id))

    def _get_candidate_by_pid(self, pid):
        """
        Finds a candidate based on pid.

        :return: candidate
        :rtype: EvalgLegacyCandidate
        """
        for candidate in self._candidates_list:
            if pid == candidate.pid:
                return candidate
        raise Exception('No user with pid={pid} found'.format(pid=pid))

    def _fetch_voters_lists(self, voters_lists_file_fp):
        """
        format: ballot_id/voter_list_id
        """
        for line in voters_lists_file_fp:
            ballot_id, voter_list_id = line.decode().strip().split('/')
            self._voters_lists_dict[ballot_id] = (
                self._pollbook_dict[voter_list_id])

    def _add_ballot_from_file(self, ballot_file_fp):
        """Loads ballot metadata from file"""
        tree = ET.parse(ballot_file_fp)
        vote_elem = tree.getroot()
        candidates_list = []
        # logger.debug("Processing ballot file %s", ballot_file_fp.name)
        ballot_id = os.path.splitext(ballot_file_fp.name)[0]
        for child in vote_elem:
            if child.tag.lower() != 'candidate':
                # should not happen (paranoia)
                logger.warning("Unexpected tag %s in ballot-file %s",
                               child.tag,
                               ballot_file_fp.name)
                continue
            try:
                candidates_list.append(self._get_candidate_by_id(
                    child.attrib['id']))
            except KeyError:
                raise EvalgLegacyInvalidBallot(
                    'Ballot {ballot_name} contains reference to unexisting '
                    'candidate {candidate_id}'.format(
                        ballot_name=ballot_file_fp.name,
                        candidate_id=child.attrib['id']))
        try:
            ballot = EvalgLegacyBallot(ballot_id,
                                       self._voters_lists_dict[ballot_id],
                                       candidates_list)
        except KeyError:
            raise EvalgLegacyInvalidBallot(
                'Ballot {ballot_name} is not found in the '
                'voters-list dict'.format(ballot_name=ballot_file_fp.name))
        # logger.debug("Adding ballot: %s", ballot)
        self._ballot_list.append(ballot)
