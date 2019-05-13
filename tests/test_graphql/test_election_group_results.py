"""
Test for all queries and mutations related to election results.

Election Group Count and Election Results.
"""


from evalg.models.election_group_count import ElectionGroupCount
from evalg.models.election_result import ElectionResult


# Election Group Count

def test_query_election_group_count_by_id(client, election_group_count_foo):
    variables = {'id': str(election_group_count_foo.id)}
    query = """
    query electionGroupCount($id: UUID!) {
        electionGroupCount(id: $id) {
            id
            groupId
            electionGroup {
                id
            }
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['electionGroupCount']
    assert str(election_group_count_foo.id) == response['id']
    assert str(election_group_count_foo.group_id) == response['groupId']


def test_query_election_group_counts(client, election_group_count_foo):
    query = """
    query electionGroupCounts {
        electionGroupCounts {
            id
            groupId
            electionGroup {
                id
            }
        }
    }
    """
    execution = client.execute(query)
    assert not execution.get('errors')
    response = execution['data']['electionGroupCounts']

    assert len(response) == 1
    assert str(election_group_count_foo.id) == response[0]['id']
    assert str(election_group_count_foo.group_id) == response[0]['groupId']


# Election Results

def test_query_election_result_by_id(client, election_result_foo):
    variables = {'id': str(election_result_foo.id)}
    query = """
    query electionResult($id: UUID!) {
        electionResult(id: $id) {
            id
            electionId
            electionGroupCountId
            votes
            result
        }
    }
    """
    execution = client.execute(query, variables=variables)

    assert not execution.get('error')
    result = execution['data']['electionResult']
    assert result
    assert str(election_result_foo.election_id) == result['electionId']
    assert str(election_result_foo.election_group_count_id) == result[
        'electionGroupCountId']

    assert result['votes'] == election_result_foo.votes
    assert result['result'] == election_result_foo.result
