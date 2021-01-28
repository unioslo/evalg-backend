import json

from evalg.graphql import get_context
from evalg.models.ballot import Envelope
from evalg.proc.pollbook import get_voters_for_person


def test_vote(db_session,
              client,
              ballot_data_generator,
              election_group_generator,
              logged_in_user):
    """Test the vote mutation."""
    election_group = election_group_generator(
        running=True,
        logged_in_user_in_census=True)
    election = election_group.elections[0]
    voter = get_voters_for_person(
        db_session,
        logged_in_user.person,
        election=election)[0]
    ballot_data = ballot_data_generator(
        election.pollbooks[0],
        candidates=election.candidates[:2])
    variables = {
        'voterId': str(voter.id),
        'ballot': json.dumps(ballot_data)
    }
    mutation = """
    mutation ($voterId: UUID!, $ballot: JSONString!) {
        vote(voterId: $voterId, ballot: $ballot) {
            ballotId
            electionId
            ok
        }
    }
    """
    execution = client.execute(mutation,
                               variables=variables,
                               context=get_context())
    assert not execution.get('errors')
    response = execution['data']['vote']
    assert response['ok']
    assert response['ballotId']

    ballot_after = Envelope.query.get(response['ballotId'])
    assert ballot_after


def test_vote_denied(db_session,
                     client,
                     ballot_data_generator,
                     election_group_generator,
                     logged_in_user):
    """
    Check that a voter can only vote i the correct election.
    """
    election_group_foo = election_group_generator(running=True)
    election_foo = election_group_foo.elections[0]
    ballot_data = ballot_data_generator(
        election_foo.pollbooks[0],
        candidates=election_foo.candidates[:2])
    election_group_bar = election_group_generator(
        running=True,
        logged_in_user_in_census=True)
    election_bar = election_group_bar.elections[0]
    voter = get_voters_for_person(
        db_session,
        logged_in_user.person,
        election=election_bar)[0]
    variables = {
        'voterId': str(voter.id),
        'ballot': json.dumps(ballot_data)
    }
    mutation = """
        mutation ($voterId: UUID!, $ballot: JSONString!) {
            vote(voterId: $voterId, ballot: $ballot) {
                ballotId
                electionId
                ok
            }
        }
        """
    execution = client.execute(mutation,
                               variables=variables,
                               context=get_context())
    assert not execution.get('errors')
    response = execution['data']['vote']
    assert response['ok'] is False
