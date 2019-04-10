import pytest

from evalg.models.candidate import Candidate
from evalg.models.election_list import ElectionList


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


def test_query_election_list_by_id(election_lists_foo, client):
    """Test the election list by id query."""
    election_list = next(iter(election_lists_foo.values()))
    variables = {'id': str(election_list.id)}
    query = """
    query($id: UUID!) {
        electionList(id: $id) {
            id
            name
            description
            informationUrl
            electionId
            candidates {
                id
                listId
                name
                meta
                informationUrl
                priority
                preCumulated
                userCumulated
            }
        }
    }
    """
    execution = client.execute(query, variables=variables)
    assert not execution.get('errors')
    response = execution['data']['electionList']

    assert str(election_list.id) == response['id']
    assert election_list.name == response['name']
    assert election_list.description == response['description']
    assert election_list.information_url == response['informationUrl']
    assert str(election_list.election_id) == response['electionId']

    assert len(election_list.candidates) == len(response['candidates'])
    assert len(response['candidates']) == 2

    foo_candidates = {str(x.id): x for x in election_list.candidates}
    response_candidates = {x['id']: x for x in response['candidates']}
    assert foo_candidates.keys() == response_candidates.keys()

    for k, v in response_candidates.items():
        candidate = foo_candidates[k]
        assert str(candidate.id) == v['id']
        assert str(candidate.list_id) == v['listId']
        assert candidate.name == v['name']
        assert candidate.meta == v['meta']
        assert candidate.information_url == v['informationUrl']
        assert candidate.priority == v['priority']
        assert candidate.pre_cumulated == v['preCumulated']
        assert candidate.user_cumulated == v['userCumulated']


def test_query_election_lists(election_lists_foo, client):
    """Test the elections query."""
    query = """
    query {
        electionLists {
            id
            name
            description
            informationUrl
            electionId
            candidates {
                id
                listId
                name
                meta
                informationUrl
                priority
                preCumulated
                userCumulated
            }
        }
    }
    """
    execution = client.execute(query)
    assert not execution.get('errors')
    response = execution['data']['electionLists']
    assert len(response) == len(election_lists_foo)

    for election_list in response:
        el_foo = election_lists_foo[election_list['id']]
        assert str(el_foo.id) == election_list['id']
        assert el_foo.name == election_list['name']
        assert el_foo.description == election_list['description']
        assert el_foo.information_url == election_list['informationUrl']
        assert str(el_foo.election_id) == election_list['electionId']

        foo_candidates = {str(x.id): x for x in el_foo.candidates}
        response_candidates = {x['id']: x for x in election_list['candidates']}
        assert foo_candidates.keys() == response_candidates.keys()

        for k, v in response_candidates.items():
            candidate = foo_candidates[k]
            assert str(candidate.id) == v['id']
            assert str(candidate.list_id) == v['listId']
            assert candidate.name == v['name']
            assert candidate.meta == v['meta']
            assert candidate.information_url == v['informationUrl']
            assert candidate.priority == v['priority']
            assert candidate.pre_cumulated == v['preCumulated']
            assert candidate.user_cumulated == v['userCumulated']


def test_delete_candidate_mutation(election_lists_foo, client):
    """Test the delete candidate mutation."""
    election_list = next(iter(election_lists_foo.values()))
    candidate = election_list.candidates[0]

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
    election_list_after = ElectionList.query.get(election_list.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        election_list.candidates) - 1
    assert candidate.id not in [x.id for x in election_list_after.candidates]


def test_add_pref_elec_candidate_mutation(election_lists_foo, client):
    """Test the add pref elec candidate mutation."""
    election_list = next(iter(election_lists_foo.values()))
    candidates_before = {str(x.id): x for x in election_list.candidates}
    variables = {
        'name': 'Foo Bar',
        'gender': 'female',
        'informationUrl': 'https://uio.no',
        'listId': str(election_list.id)
    }

    mutation = """
    mutation (
        $name: String!
        $gender: String!
        $informationUrl: String
        $listId: UUID!
    ) {
        addPrefElecCandidate(
            name: $name
            gender: $gender
            informationUrl: $informationUrl
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
    election_list_after = ElectionList.query.get(election_list.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        candidates_before) + 1
    for candidate in election_list_after.candidates:
        if str(candidate.id) not in candidates_before:
            assert candidate.name == variables['name']
            assert candidate.information_url == variables['informationUrl']
            assert str(candidate.list_id) == variables['listId']
            assert candidate.meta['gender'] == variables['gender']
            break


def test_update_pref_elec_candidate_mutation(election_lists_foo, client):
    """Test the update pref elec candidate mutation."""
    election_list = next(iter(election_lists_foo.values()))
    candidates_before = election_list.candidates
    candidate_before = election_list.candidates[0]
    variables = {
        'id': str(candidate_before.id),
        'name': 'Foo Bar',
        'gender': 'female' if candidate_before.meta['gender'] == 'male' else 'male',
        'informationUrl': 'https://uio.no/annen/enhet',
        # Use the same list_id, there should never be a need to change the
        # list_id of candidate
        'listId': str(candidate_before.list_id)
    }
    mutation = """
    mutation (
        $id: UUID!
        $name: String!
        $gender: String!
        $informationUrl: String
        $listId: UUID!
    ) {
        updatePrefElecCandidate(
            id: $id
            name: $name
            gender: $gender
            informationUrl: $informationUrl
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
    election_list_after = ElectionList.query.get(election_list.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        candidates_before)
    candidate_after = Candidate.query.get(candidate_before.id)
    assert candidate_after.list_id == candidate_before.list_id
    assert candidate_after.name != candidate_before.name
    assert candidate_after.name == variables['name']
    assert candidate_after.information_url != candidate_before.information_url
    assert candidate_after.information_url == variables['informationUrl']
    assert candidate_after.meta['gender'] != candidate_before.meta['gender']
    assert candidate_after.meta['gender'] == variables['gender']


def test_add_team_pref_elec_candidate_mutation(election_lists_foo, client):
    """Test the add pref elec candidate mutation."""
    election_list = list(iter(election_lists_foo.values()))[-1]
    candidates_before = {str(x.id): x for x in election_list.candidates}
    variables = {
        'name': 'Foo Bar',
        'coCandidates': [{'name': 'Bar Baz'}, {'name': 'Jane Doe'}],
        'informationUrl': 'https://uio.no',
        'listId': str(election_list.id)
    }

    mutation = """
    mutation (
        $name: String!
        $coCandidates: [CoCandidatesInput]!
        $informationUrl: String
        $listId: UUID!
    ) {
        addTeamPrefElecCandidate(
        name: $name
        coCandidates: $coCandidates
        informationUrl: $informationUrl
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
    election_list_after = ElectionList.query.get(election_list.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(
        candidates_before) + 1
    for candidate in election_list_after.candidates:
        if str(candidate.id) not in candidates_before:
            assert candidate.name == variables['name']
            assert candidate.information_url == variables['informationUrl']
            assert str(candidate.list_id) == variables['listId']
            assert candidate.meta['co_candidates'] == variables['coCandidates']
            break


def test_update_team_pref_elec_candidate_mutation(election_lists_foo, client):
    """Test the update team pref elec candidate mutation."""
    election_list = list(iter(election_lists_foo.values()))[-1]
    candidates_before = election_list.candidates
    candidate_before = candidates_before[0]
    variables = {
        'id': str(candidate_before.id),
        'name': 'Foo Bar',
        'coCandidates': [{'name': 'Bar Baz'}, {'name': 'Jane Doe'}],
        'informationUrl': 'https://uio.no/annen/enhet',
        # Use the same list_id, there should never be a need to change the
        # list_id of candidate
        'listId': str(candidate_before.list_id)
    }
    mutation = """
    mutation (
        $id: UUID!
        $name: String!
        $coCandidates: [CoCandidatesInput]!
        $informationUrl: String
        $listId: UUID!
    ) {
        updateTeamPrefElecCandidate(
        id: $id
        name: $name
        coCandidates: $coCandidates
        informationUrl: $informationUrl
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
        candidates_before)
    candidate_after = Candidate.query.get(candidate_before.id)
    assert candidate_after.list_id == candidate_before.list_id
    assert candidate_after.name != candidate_before.name
    assert candidate_after.name == variables['name']
    assert candidate_after.information_url != candidate_before.information_url
    assert candidate_after.information_url == variables['informationUrl']
    assert candidate_after.meta['co_candidates'] != candidate_before.meta['coCandidates']
    assert candidate_after.meta['co_candidates'] == variables['coCandidates']
