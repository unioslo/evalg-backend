

from evalg.models.ballot import Envelope
from evalg.models.votes import Vote
from evalg.ballot_serializer.base64_nacl import Base64NaClSerializer


def test_election_vote_policy(
        config,
        election_group_generator,
        ballot_data_generator,
        election_vote_policy_generator,
        election_keys):
    """
    Test the election vote policy flow.

    Tests a normal vote, with at valid vote, valid election etc.
    """
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='uio_stv',
                                              candidates_per_pollbook=7,
                                              nr_of_seats=2,
                                              voters_with_votes=False)
    election = election_group.elections[0]
    pollbook = election.pollbooks[0]
    voter = pollbook.voters[0]
    candidate = election.lists[0].candidates[0]

    ballot_data = ballot_data_generator(pollbook, candidates=[candidate])

    election_vote_policy = election_vote_policy_generator(voter.id)
    assert election_vote_policy.envelope_type == config.ENVELOPE_TYPE
    vote = election_vote_policy.add_vote(ballot_data.copy())
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
        election_private_key=election_keys['private'],
    )

    assert serializer
    ballot_after = serializer.deserialize(encrypted_ballot_data)
    assert ballot_after
    assert ballot_after == ballot_data
