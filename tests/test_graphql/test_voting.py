import json

from evalg.graphql import get_context
from evalg.models.ballot import Envelope


def test_vote(client, election_pref_vote, pollbook_voter_foo):
    """Test the vote mutation."""

    variables = {
        'voterId': str(pollbook_voter_foo.id),
        'ballot': json.dumps(election_pref_vote)
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
    # TODO decrypt and check ballot contents.
