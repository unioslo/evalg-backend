import pytest

from evalg.counting.legacy import EvalgLegacyElection
from evalg.counting.algorithms import uitstv

import logging


@pytest.mark.parametrize(
    "electionFile, expected_ranking",
    [
        (
            "tests/test_counting/election_data/uitstv_election_data.zip",
            [
                "12",
                "13",
                "4",
                "7",
                "5",
                "1",
                "6",
                "3",
                "10",
                "2",
                "11",
                "8",
                "9",
            ],
        )
    ],
)
def test_get_result(electionFile, expected_ranking):
    election = EvalgLegacyElection(electionFile)
    result, _ = uitstv.get_result(election)
    assert result["ranked_candidates"] == expected_ranking
