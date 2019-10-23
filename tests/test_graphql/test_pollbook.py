
import evalg.database.query

from evalg.graphql import get_context
from evalg.models.pollbook import Pollbook


def test_get_pollbook_by_id(db_session, client, pollbook_foo, logged_in_user):
    """Test fetching pollbook by id."""
    variables = {'id': str(pollbook_foo.id)}
    query = """
    query pollbook($id: UUID!) {
        pollbook(id: $id) {
            id
            name
        }
    }
    """
    context = get_context()
    execution = client.execute(query, variables=variables, context=context)
    assert not execution.get('errors')
    response = execution['data']['pollbook']
    assert str(pollbook_foo.id) == response['id']
    assert pollbook_foo.name == response['name']


def test_pollbook_voting_report(client,
                                logged_in_user,
                                make_full_election):
    """Test the pollbook voting report."""
    full_election = make_full_election('Test voting report')
    pollbook = full_election['elections'][0].pollbooks[0]
    variables = {'id': str(pollbook.id)}

    query = """
    query pollbook($id: UUID!) {
      pollbook(id: $id) {
        id
        votersWithVote {
          id
        }
        votersWithoutVote {
          id
        }
      }
    }
    """
    execution = client.execute(query,
                               variables=variables,
                               context=get_context())
    assert not execution.get('errors')
    pollbook_response = execution['data']['pollbook']
    assert pollbook_response

    pollbook_voters = full_election['pollbook_voters'][pollbook_response['id']]
    pollbook_voters_ids = [str(x.id) for x in pollbook_voters]

    voters_with_vote_ids = [
        str(x.voter_id) for x in full_election['votes'] if
        str(x.voter_id) in pollbook_voters_ids]
    voters_without_vote_ids = [
        str(x.id) for x in pollbook_voters if
        str(x.id) not in voters_with_vote_ids]

    for voter in pollbook_response['votersWithVote']:
        assert voter['id'] in voters_with_vote_ids
        assert voter['id'] not in voters_without_vote_ids
    for voter in pollbook_response['votersWithoutVote']:
        assert voter['id'] not in voters_with_vote_ids
        assert voter['id'] in voters_without_vote_ids
