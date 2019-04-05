import pytest

def test_query_electiongroup_by_id(group_foo, client):
    variables = {'id': str(group_foo.id)}
    query = """
    query electionGroup($id: UUID!) {
        electionGroup(id: $id) {
            name
            description
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['electionGroup']
    assert group_foo.name == response['name']
    assert group_foo.description == response['description']
