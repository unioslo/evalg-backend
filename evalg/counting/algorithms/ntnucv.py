# -*- coding: utf-8 -*-
"""
Implementation of NTNU's cumulative voting algorithm used by USN

TODO: Events and protocol template to be created
"""
import collections
import decimal
import logging

from evalg.counting import base


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)


class Result(base.Result):
    """NTNUCV Result"""

    def __init__(self, meta, candidates):
        """
        :param meta: The metadata for this result
        :type meta: dict

        :param candidates: The elected regular candidates
        :type candidates: collections.abc.Sequence
        """
        super().__init__(meta)
        self.regular_candidates = candidates
        self.substitute_candidates = tuple()


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
        for vcount in count_results:
            candidate, candidate_count = vcount
            logger.info("Candidate %s: %s -> %s",
                        candidate,
                        str(count_result_stats[candidate].items()),
                        candidate_count)
        self._state.final = True
        return self._state
