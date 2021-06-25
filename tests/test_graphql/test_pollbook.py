

from evalg.graphql import get_context


def test_pollbook_voting_report(client,
                                logged_in_user,
                                election_group_generator):
    """Test the pollbook voting report."""
    election_group = election_group_generator(owner=True,
                                              countable=True,
                                              multiple=True,
                                              election_type='uio_stv',
                                              candidates_per_pollbook=7,
                                              nr_of_seats=2,
                                              voters_with_votes=True)
    election = election_group.elections[0]

    pollbook = election.pollbooks[0]
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
    pollbook_voters = pollbook.voters

    voters_with_vote_ids = [
        str(x.id) for x in pollbook_voters if
        x.has_voted]
    voters_without_vote_ids = [
        str(x.id) for x in pollbook_voters if
        not x.has_voted]

    for voter in pollbook_res['votersWithVote']:
        assert voter['id'] in voters_with_vote_ids
        assert voter['id'] not in voters_without_vote_ids
    for voter in pollbook_res['votersWithoutVote']:
        assert voter['id'] not in voters_with_vote_ids
        assert voter['id'] in voters_without_vote_ids
