import pytest

from evalg.models.candidate import Candidate
from evalg.models.election_list import ElectionList


def test_query_electiongroup_by_id(election_group_foo, client):
    variables = {'id': str(election_group_foo.id)}
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
    assert election_group_foo.name == response['name']
    assert election_group_foo.description == response['description']


def test_query_elections(election_foo, client):
    query = """
    query elections {
        elections {
            id
            name
            description
        }
    }
    """
    execution = client.execute(query)
    assert not execution.get('errors')
    response = execution['data']['elections']
    assert len(response) == 1
    assert str(election_foo.id) == response[0]['id']
    assert election_foo.name == response[0]['name']
    assert election_foo.description == response[0]['description']


def test_query_election_by_id(election_foo, client):
    variables = {'id': str(election_foo.id)}
    query = """
    query election($id: UUID!) {
        election(id: $id) {
            id
            name
            description
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['election']
    assert str(election_foo.id) == response['id']
    assert election_foo.name == response['name']
    assert election_foo.description == response['description']


def test_query_election_list_by_id(pref_candidates_foo,
                                   election_list_pref_foo,
                                   client):
    """Test the election list by id query."""
    variables = {'id': str(election_list_pref_foo.id)}
    query = """
    query($id: UUID!) {
        electionList(id: $id) {
            id
            name
            candidates {
                id
                listId
                name
                meta
            }
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['electionList']
    assert str(election_list_pref_foo.id) == response['id']
    assert election_list_pref_foo.name == response['name']
    assert len(pref_candidates_foo) == len(response['candidates'])
    foo_candidates = {str(x.id): x for x in election_list_pref_foo.candidates}
    response_candidates = {x['id']: x for x in response['candidates']}
    assert foo_candidates.keys() == response_candidates.keys()
    for k, v in response_candidates.items():
        candidate = foo_candidates[k]
        assert str(candidate.id) == v['id']
        assert str(candidate.list_id) == v['listId']
        assert candidate.name == v['name']
        assert candidate.meta == v['meta']


def test_query_election_list(election_list_pref_foo, client):
    """Test the elections query."""
    query = """
    query {
        electionLists {
            id
            name
            candidates {
                id
                listId
                name
                meta
            }
        }
    }
    """
    execution = client.execute(query)
    assert not execution.get('errors')
    response = execution['data']['electionLists']
    assert len(response) == 1
    foo_candidates = {str(x.id): x for x in election_list_pref_foo.candidates}
    response_candidates = {x['id']: x for x in response[0]['candidates']}
    assert foo_candidates.keys() == response_candidates.keys()

    for k, v in response_candidates.items():
        candidate = foo_candidates[k]
        assert str(candidate.id) == v['id']
        assert str(candidate.list_id) == v['listId']
        assert candidate.name == v['name']
        assert candidate.meta == v['meta']


def test_delete_candidate_mutation(pref_candidates_foo, election_list_pref_foo,
                                   client):
    """Test the delete candidate mutation."""
    candidate = pref_candidates_foo[0]

    variables = {'id': str(candidate.id)}
    mutation = """
    mutation ($id: UUID!) {
        deleteCandidate(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(mutation, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['deleteCandidate']
    assert response['ok']
    candidate_after = Candidate.query.get(candidate.id)
    assert candidate_after is None
    election_list_after = ElectionList.query.get(election_list_pref_foo.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        pref_candidates_foo) - 1
    assert candidate.id not in [x.id for x in election_list_after.candidates]


def test_add_pref_elec_candidate_mutation(election_list_pref_foo, client):
    """Test the add pref elec candidate mutation."""
    candidates_before = {str(x.id): x for x in
                         election_list_pref_foo.candidates}
    variables = {
        'name': 'Foo Bare',
        'gender': 'female',
        'listId': str(election_list_pref_foo.id)
    }
    mutation = """
    mutation (
        $name: String!
        $gender: String!
        $listId: UUID!
    ) {
        addPrefElecCandidate(
            name: $name
            gender: $gender
            listId: $listId
        ) {
            ok
        }
    }
    """
    execution = client.execute(mutation, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['addPrefElecCandidate']
    assert response['ok']

    # Get new election list
    election_list_after = ElectionList.query.get(election_list_pref_foo.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        candidates_before) + 1
    for candidate in election_list_after.candidates:
        if str(candidate.id) not in candidates_before:
            assert candidate.name == variables['name']
            assert str(candidate.list_id) == variables['listId']
            assert candidate.meta['gender'] == variables['gender']
            break


def test_update_pref_elec_candidate_mutation(pref_candidates_foo,
                                             client):
    """Test the update pref elec candidate mutation."""
    candidate_before = pref_candidates_foo[0]

    election_list = ElectionList.query.get(candidate_before.list_id)

    variables = {
        'id': str(candidate_before.id),
        'name': 'FooBar',
        'gender': 'Female' if candidate_before.meta['gender'] == 'Male' else
        'Female',
        'listId': str(candidate_before.list_id)
    }
    mutation = """
    mutation (
        $id: UUID!
        $name: String!
        $gender: String!
        $listId: UUID!
    ) {
        updatePrefElecCandidate(
            id: $id
            name: $name
            gender: $gender
            listId: $listId
        ) {
            ok
        }
    }
    """
    execution = client.execute(mutation, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['updatePrefElecCandidate']
    assert response['ok']

    # Get new election list
    election_list_after = ElectionList.query.get(candidate_before.list.id)

    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        election_list.candidates)
    candidate_after = Candidate.query.get(candidate_before.id)
    assert candidate_after.list_id == candidate_before.list_id
    assert candidate_after.name != candidate_before.name
    assert candidate_after.name == variables['name']
    assert candidate_after.meta['gender'] != candidate_before.meta['gender']
    assert candidate_after.meta['gender'] == variables['gender']


def test_add_team_pref_elec_candidate_mutation(election_list_team_pref_foo,
                                               client):
    """Test the add pref elec candidate mutation."""
    candidates_before = {str(x.id): x for x in
                         election_list_team_pref_foo.candidates}
    variables = {
        'name': 'Foo Bar',
        'coCandidates': [{'name': 'Bar Baz'}, {'name': 'Jane Doe'}],
        'listId': str(election_list_team_pref_foo.id)
    }

    mutation = """
    mutation (
        $name: String!
        $coCandidates: [CoCandidatesInput]!
        $listId: UUID!
    ) {
        addTeamPrefElecCandidate(
        name: $name
        coCandidates: $coCandidates
        listId: $listId
        ) {
        ok
        }
    }
    """

    execution = client.execute(mutation, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['addTeamPrefElecCandidate']
    assert response['ok']
    # Get new election list
    election_list_after = ElectionList.query.get(
        election_list_team_pref_foo.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        candidates_before) + 1
    for candidate in election_list_after.candidates:
        if str(candidate.id) not in candidates_before:
            assert candidate.name == variables['name']
            assert str(candidate.list_id) == variables['listId']
            assert candidate.meta['co_candidates'] == variables['coCandidates']
            break


def test_update_team_pref_elec_candidate_mutation(
        team_pref_candidates_foo,
        client):
    """Test the update team pref elec candidate mutation."""

    candidate_before = team_pref_candidates_foo[0]

    election_list = ElectionList.query.get(candidate_before.list_id)

    variables = {
        'id': str(candidate_before.id),
        'name': 'Foo Bar',
        'coCandidates': [{'name': 'Bar Baz'}, {'name': 'Jane Doe'}],
        'listId': str(candidate_before.list_id)
    }
    mutation = """
    mutation (
        $id: UUID!
        $name: String!
        $coCandidates: [CoCandidatesInput]!
        $listId: UUID!
    ) {
        updateTeamPrefElecCandidate(
        id: $id
        name: $name
        coCandidates: $coCandidates
        listId: $listId
        ) {
            ok
        }
    }
    """
    execution = client.execute(mutation, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['updateTeamPrefElecCandidate']
    assert response['ok']

    # Get new election list
    election_list_after = ElectionList.query.get(election_list.id)
    assert election_list_after is not None

    assert len(election_list_after.candidates) == len(
        election_list.candidates)

    candidate_after = Candidate.query.get(candidate_before.id)
    assert candidate_after.list_id == candidate_before.list_id
    assert candidate_after.name != candidate_before.name
    assert candidate_after.name == variables['name']
    assert candidate_after.meta['co_candidates'] != candidate_before.meta['coCandidates']
    assert candidate_after.meta['co_candidates'] == variables['coCandidates']
