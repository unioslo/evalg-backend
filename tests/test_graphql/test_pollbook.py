

from evalg.graphql import get_context


def test_pollbook_voting_report(client,
                                logged_in_user,
                                make_full_election):
    """Test the pollbook voting report."""
    full_election = make_full_election('Test voting report')
    election_group = full_election['election_group']
    pollbook = full_election['elections'][0].pollbooks[0]
    variables = {'id': str(election_group.id)}

    query = """
    query electionGroup($id: UUID!) {
      electionGroup(id: $id) {
        id
        elections {
          id
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
      }
    }
    """
    execution = client.execute(query,
                               variables=variables,
                               context=get_context())
    assert not execution.get('errors')
    response = execution['data']['electionGroup']
    assert response

    pollbook_res = response['elections'][0]['pollbooks'][0]

    pollbook_voters = full_election['pollbook_voters'][pollbook_res['id']]
    pollbook_voters_ids = [str(x.id) for x in pollbook_voters]

    voters_with_vote_ids = [
        str(x.voter_id) for x in full_election['votes'] if
        str(x.voter_id) in pollbook_voters_ids]
    voters_without_vote_ids = [
        str(x.id) for x in pollbook_voters if
        str(x.id) not in voters_with_vote_ids]

    for voter in pollbook_res['votersWithVote']:
        assert voter['id'] in voters_with_vote_ids
        assert voter['id'] not in voters_without_vote_ids
    for voter in pollbook_res['votersWithoutVote']:
        assert voter['id'] not in voters_with_vote_ids
        assert voter['id'] in voters_without_vote_ids
