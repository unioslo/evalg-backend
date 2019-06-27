
import evalg.database.query

from evalg.graphql import get_context
from evalg.models.pollbook import PollBook


def test_get_pollbook_by_id(client, pollbook_foo):
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
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['pollbook']
    assert str(pollbook_foo.id) == response['id']
    assert pollbook_foo.name == response['name']


def test_get_pollbooks(db_session, client, make_full_election):
    """Test fetching all pollbooks."""
    # Create more election data
    make_full_election('Test get pollbooks')

    query = """
    query pollbooks {
        pollbooks {
            id
            name
        }
    }
    """
    execution = client.execute(query)
    assert not execution.get('errors')
    response = execution['data']['pollbooks']
    pollbooks = db_session.query(PollBook).all()
    assert len(response) == len(pollbooks)


def test_pollbook_voting_report(client, make_full_election):
    """Test the pollbook voting report."""
    full_election = make_full_election('Test voting report')
    query = """
    query pollbooks {
      pollbooks {
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
    execution = client.execute(query, context=get_context())
    assert not execution.get('errors')
    response = execution['data']['pollbooks']
    assert response

    for pollbook in response:
        if pollbook['id'] not in full_election['pollbook_voters']:
            # We only look at the pollbooks we created in this test.
            continue
        pollbook_voters = full_election['pollbook_voters'][pollbook['id']]
        pollbook_voters_ids = [str(x.id) for x in pollbook_voters]

        voters_with_vote_ids = [
            str(x.voter_id) for x in full_election['votes'] if
            str(x.voter_id) in pollbook_voters_ids]

        voters_without_vote_ids = [
            str(x.id) for x in pollbook_voters if
            str(x.id) not in voters_with_vote_ids]

        for voter in pollbook['votersWithVote']:
            assert voter['id'] in voters_with_vote_ids
            assert voter['id'] not in voters_without_vote_ids
        for voter in pollbook['votersWithoutVote']:
            assert voter['id'] not in voters_with_vote_ids
            assert voter['id'] in voters_without_vote_ids
