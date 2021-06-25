"""
Test for all queries and mutations related to election results.

Election Group Count and Election Results.
"""

from evalg.graphql import get_context


# Election Group Count

def test_query_election_group_count_by_id(client,
                                          election_group_generator):
    election_group = election_group_generator(
        owner=True,
        counted=True
    )
    election_group_count = election_group.election_group_counts[0]
    variables = {'id': str(election_group_count.id)}
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
    context = get_context()
    execution = client.execute(query, variables=variables, context=context)
    assert not execution.get('errors')
    response = execution['data']['electionGroupCount']
    assert str(election_group_count.id) == response['id']
    assert str(election_group_count.group_id) == response['groupId']


def test_mutation_start_election_group_count(client,
                                             db_session,
                                             election_group_generator,
                                             election_keys):
    election_group = election_group_generator(owner=True,
                                              multiple=True,
                                              countable=True,
                                              with_key=True)
    variables = {
        'id': str(election_group.id),
        'electionKey': election_keys['private']
    }
    mutation = """
        mutation startElectionGroupCount($id: UUID!, $electionKey: String!) {
            startElectionGroupCount(id: $id, electionKey: $electionKey) {
                success
                code
                message
            }
        }
        """
    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
    assert not execution.get('errors')
    result = execution['data']['startElectionGroupCount']
    assert result['success']


def test_mutation_start_election_group_count_responses(
        client,
        db_session,
        election_group_generator,
        election_keys):
    """Verify that the mutation gives correct responses when the count fails"""
    election_group = election_group_generator(
        owner=True,
        running=True
    )
    variables = {
        'id': str(election_group.id),
        'electionKey': election_keys['private']
    }
    mutation = """
    mutation startElectionGroupCount($id: UUID!, $electionKey: String!) {
        startElectionGroupCount(id: $id, electionKey: $electionKey) {
            success
            code
            message
        }
    }
    """
    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
    assert not execution.get('errors')
    result = execution['data']['startElectionGroupCount']
    # The mutation should fail because election_foo is not closed
    assert (not result['success'] and
            result['code'] == 'cannot-count-before-all-elections-are-closed')

    variables = {
        'id': str(election_group.id),
        'electionKey': election_keys['public']
    }
    execution = client.execute(mutation, variables=variables,
                               context=context)
    assert not execution.get('errors')
    result = execution['data']['startElectionGroupCount']
    # The mutation should fail because the wrong code is given
    assert (not result['success'] and
            result['code'] == 'invalid-election-key')


def test_query_election_group_counting_results(client,
                                               db_session,
                                               election_group_generator):
    election_group = election_group_generator(
        owner=True,
        counted=True
    )
    election_group_count = election_group.election_group_counts[0]

    variables = {'id': str(election_group.id)}
    query = """
    query electionGroupCountingResults($id: UUID!) {
        electionGroupCountingResults(id: $id) {
            id
            groupId
            electionGroup {
                id
            }
        }
    }
    """
    context = get_context()
    execution = client.execute(query, variables=variables, context=context)
    assert not execution.get('errors')
    response = execution['data']['electionGroupCountingResults']

    assert len(response) == 1
    assert str(election_group_count.id) == response[0]['id']
    assert str(election_group_count.group_id) == response[0]['groupId']


# Election Results

def test_query_election_result_by_id(client,
                                     db_session,
                                     election_group_generator):
    election_group = election_group_generator(
        owner=True,
        counted=True
    )
    election_result = election_group.elections[0].election_results[0]
    variables = {'id': str(election_result.id)}
    query = """
    query electionResult($id: UUID!) {
        electionResult(id: $id) {
            id
            electionId
            electionGroupCountId
            ballots
            result
        }
    }
    """
    context = get_context()
    execution = client.execute(query, variables=variables, context=context)
    assert not execution.get('error')
    result = execution['data']['electionResult']
    assert result
    assert str(election_result.election_id) == result['electionId']
    assert str(election_result.election_group_count_id) == result[
        'electionGroupCountId']

    assert result['ballots'] == election_result.ballots
    assert result['result'] == election_result.result
