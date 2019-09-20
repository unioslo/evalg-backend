

from evalg.models.ballot import Envelope
from evalg.models.votes import Vote
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer


def test_election_vote_policy(
        config,
        pollbook_voter_foo,
        make_election_vote_policy,
        election_pref_vote,
        election_keys_foo):
    """
    Test the election vote policy flow.

    Tests a normal vote, with at valid vote, valid election etc.
    """
    election_vote_policy = make_election_vote_policy(pollbook_voter_foo.id)
    assert election_vote_policy.envelope_type == config.ENVELOPE_TYPE
    vote = election_vote_policy.add_vote(election_pref_vote.copy())
    assert vote
    assert election_vote_policy.get_voter(vote.voter_id)

    # get and check vote
    vote_after = Vote.query.get(vote.voter_id)
    assert vote_after
    assert vote_after.ballot_id == vote.ballot_id
    envelope_after = Envelope.query.get(vote_after.ballot_id)
    assert envelope_after
    encrypted_ballot_data = envelope_after.ballot_data
    assert encrypted_ballot_data

    # Deserialize and decrypt the ballot
    serializer = Base64NaClSerializer(
        backend_public_key=config.BACKEND_PUBLIC_KEY,
        election_private_key=election_keys_foo['private'],
    )

    assert serializer
    ballot_after = serializer.deserialize(encrypted_ballot_data)
    assert ballot_after
    assert ballot_after == election_pref_vote

