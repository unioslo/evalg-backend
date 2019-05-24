# -*- coding: utf-8 -*-
"""
Abstract classes for the counting package

This set of abstract classes should serve as a guideline and "practical"
documentation for the developers of the eValg model classes.
Hopefully it will be updated on regular bases.
"""
import abc


class EvalgCountingAbstractBase(abc.ABC):
    """
    Used only to illustrate that the following attributes should be present in
    all classes "based" on EvalgCountingAbstractBase.

    This type of inheritance is not valid in Python.
    """

    @abc.abstractmethod
    def __str__(self):
        pass


class AbstractCensus(EvalgCountingAbstractBase):

    @property
    @abc.abstractmethod
    def ballots_count(self):
        """ballots_count-property"""
        pass

    @property
    @abc.abstractmethod
    def counting_ballots_count(self):
        """counting_ballots_count-property"""
        pass

    @property
    @abc.abstractmethod
    def empty_ballots_count(self):
        """empty_ballots_count-property"""
        pass

    @property
    @abc.abstractmethod
    def name(self):
        """candidate_id-property"""
        pass

    @property
    @abc.abstractmethod
    def weight_per_census(self):
        """weight_per_census-property"""
        pass

    @property
    @abc.abstractmethod
    def weight_per_vote(self):
        """weight_per_vote-property"""
        pass


class AbstractCandidate(EvalgCountingAbstractBase):
    pass


class AbstractQuota(EvalgCountingAbstractBase):

    @property
    @abc.abstractmethod
    def members(self):
        """members-property"""
        pass

    @property
    @abc.abstractmethod
    def min_value(self):
        """min_value-property"""
        pass

    @property
    @abc.abstractmethod
    def name(self):
        """name-property"""
        pass


class AbstractBallot(EvalgCountingAbstractBase):

    @property
    @abc.abstractmethod
    def candidates(self):
        """candidates-property"""
        pass

    @property
    @abc.abstractmethod
    def census(self):
        """census-property"""
        pass

    @property
    @abc.abstractmethod
    def raw_string(self):
        """
        A string based on voters_lists_id and candidates
        to be used for sorting / raw representation ballots
        """
        pass


class AbstractElection(EvalgCountingAbstractBase):

    @property
    @abc.abstractmethod
    def ballots(self):
        """ballots property"""
        pass

    @property
    @abc.abstractmethod
    def candidates(self):
        """candidates property"""
        pass

    @property
    @abc.abstractmethod
    def census_lists(self):
        """census_lists-property"""
        # for debugging in Count
        pass

    @property
    @abc.abstractmethod
    def election_type(self):
        """election_type-property"""
        pass

    @property
    @abc.abstractmethod
    def num_choosable(self):
        """num_choosable-property"""
        pass

    @property
    @abc.abstractmethod
    def num_substitutes(self):
        """num_substitutes-property"""
        pass

    @property
    @abc.abstractmethod
    def quotas(self):
        """quotas-property"""
        pass

    @property
    def total_amount_empty_ballots(self):
        """total_amount_empty_ballots-property"""
        # for debugging in Count
        pass

    @property
    def total_amount_ballots(self):
        """total_amount_ballots-property"""
        # for debugging in Count
        pass

    @property
    def total_amount_counting_ballots(self):
        """total_amount_counting_ballots-property"""
        # for debugging in Count
        pass
