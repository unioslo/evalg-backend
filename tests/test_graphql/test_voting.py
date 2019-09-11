import json

from evalg.graphql import get_context
from evalg.models.ballot import Envelope


def test_vote(db_session, client, pollbook_foo, make_pollbook_voter,
              make_pollbook_vote, election_pref_vote, logged_in_user):
    """Test the vote mutation."""
    voter = make_pollbook_voter(person=logged_in_user.person,
                                pollbook=pollbook_foo)

    variables = {
        'voterId': str(voter.id),
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


def test_vote_denied(db_session, client, election_pref_vote,
                     pollbook_voter_bar, logged_in_user):

    variables = {
        'voterId': str(pollbook_voter_bar.id),
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
    assert response['ok'] is False
