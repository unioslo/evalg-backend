""" evalg version utils """
import os
import pkg_resources


DISTRIBUTION_NAME = 'evalg'


def get_distribution():
    """Get the distribution object for this single module dist."""
    try:
        return pkg_resources.get_distribution(DISTRIBUTION_NAME)
    except pkg_resources.DistributionNotFound:
        return pkg_resources.Distribution(
            project_name=DISTRIBUTION_NAME,
            version='0.0.0',
            location=os.path.dirname(__file__))
