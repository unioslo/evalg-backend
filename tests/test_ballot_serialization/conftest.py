import pytest

from evalg.serializer import Base64NaClSerializer

@pytest.fixture
def election_keys():
    return {
        "backend_private_key": "nnQjcDrXcIc8mpHabme8j7/xPBWqIkPElM8KtAJ4vgc=",
        "backend_public_key": "KLUDKkCPrAEcK9SrYDyMsrLEShm6axS9uSG/sOfibCA=",
        "election_public_key": "G8g0YvWaLgFBEwpjxzQBxgaRlEprD0AlVHKw+3ImTnc=",
        "election_private_key": "4dwhka4ewi0fRbz/gBcHttejUz/vcExaqH7bFWsrM8E=",
    }


@pytest.fixture
def ballot_serializer(election_keys):
    return Base64NaClSerializer(
        election_public_key=election_keys['election_public_key'],
        election_private_key=election_keys['election_private_key'],
        backend_public_key=election_keys['backend_public_key'],
        backend_private_key=election_keys['backend_private_key'])


@pytest.fixture
def ballot():
    return {
        'electionId': '583cb3dd-676c-43c5-8811-431be577d26c',
        'selectedPollbookId': '1c93109b-54eb-48d0-aa01-02c5d3bc0599',
        'ballotData': {
            'voteType': 'majorityVote',
            'isBlankVote': True,
            'candidateId': None,
        }
    }

