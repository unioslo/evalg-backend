"""
This module implements quota rules

"""
import math


class Quota:
    def __init__(self, members, min_value, name):
        self.members = members
        self.min_value = min_value
        self.name = name


def create_gender_40_quota(candidates, gender, num_choosable):
    """Create a gender_40 quota for the desired gender (IV §16)

    :param candidates: list of all candidates in the election
    :param gender: 'male' or 'female'
    :param num_choosable: number of candidates to be elected
    """
    name = 'gender_40_{}'.format(gender)
    members = list(
        filter(
            lambda cand: cand.meta['gender'] == gender,
            candidates
        )
    )
    if num_choosable <= 1:
        return []
    elif num_choosable <= 3:
        return [Quota(members, 1, name)]
    else:
        min_value = math.ceil(0.4*num_choosable)
        return [Quota(members, min_value, name)]


def create_gender_40_quotas(candidates, num_choosable):
    """Create gender_40 quotas for both genders (IV §16)

    :param candidates: list of all candidates in the election
    :param num_choosable: number of candidates to be elected
    """
    quotas = []
    quotas.extend(
        create_gender_40_quota(candidates, 'male', num_choosable)
    )
    quotas.extend(
        create_gender_40_quota(candidates, 'female', num_choosable)
    )
    return quotas


quota_name2method = {'gender_40': create_gender_40_quotas}
