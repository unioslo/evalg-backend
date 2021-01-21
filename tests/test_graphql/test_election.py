from evalg.models.candidate import Candidate
from evalg.models.election_list import ElectionList
from evalg.models.election import ElectionGroup
from evalg.graphql import get_context


def test_query_electiongroup_by_id(make_election_group,
                                   client,
                                   logged_in_user):
    election_group = make_election_group('Test query EG by id')
    variables = {'id': str(election_group.id)}
    query = """
    query electionGroup($id: UUID!) {
        electionGroup(id: $id) {
            id
            name
            description
        }
    }
    """
    execution = client.execute(
        query, variables=variables, context=get_context())
    assert not execution.get('errors')
    response = execution['data']['electionGroup']
    assert str(election_group.id) == response['id']
    assert election_group.name == response['name']
    assert election_group.description == response['description']


def test_publish_election_group(
        db_session,
        client,
        logged_in_user,
        make_election_group,
        make_election,
        make_person_publisher):

    election_group = make_election_group('Test publish EG', admin=True)
    election_group.unpublish()
    election_group.unannounce()

    election = make_election('test_publish_election',
                             election_group=election_group)

    election.active = True

    db_session.flush()
    assert not election_group.published

    make_person_publisher(db_session, logged_in_user.person)
    variables = {'id': str(election_group.id)}
    mutation = """
    mutation ($id: UUID!) {
        publishElectionGroup(id: $id) {
            success
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['publishElectionGroup']
    assert response['success']
    election_group_after_after = ElectionGroup.query.get(election_group.id)
    assert election_group_after_after.published


def test_unpublish_election_group(
        db_session,
        client,
        logged_in_user,
        make_election_group,
        make_person_publisher):
    election_group = make_election_group('Test unpublish EG', admin=True)
    db_session.flush()
    assert election_group.published

    make_person_publisher(db_session, logged_in_user.person)
    variables = {'id': str(election_group.id)}
    mutation = """
    mutation ($id: UUID!) {
        unpublishElectionGroup(id: $id) {
            success
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['unpublishElectionGroup']
    assert response['success']
    election_group_after_after = ElectionGroup.query.get(election_group.id)
    assert not election_group_after_after.published


def test_delete_candidate_mutation(db_session,
                                   client,
                                   logged_in_user,
                                   election_group_generator):
    """Test the delete candidate mutation."""
    election_group = election_group_generator(
        owner=logged_in_user.person)
    election_list = election_group.elections[0].lists[0]
    candidates_before = {str(x.id): x for x in
                         election_list.candidates}
    candidate = election_list.candidates[0]

    variables = {'id': str(candidate.id)}
    mutation = """
    mutation ($id: UUID!) {
        deleteCandidate(id: $id) {
            ok
        }
    }
    """
    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
    assert not execution.get('errors')
    response = execution['data']['deleteCandidate']
    assert response['ok']
    candidate_after = Candidate.query.get(candidate.id)
    assert candidate_after is None
    election_list_after = ElectionList.query.get(election_list.id)
    assert election_list_after is not None
    assert len(election_list_after.candidates) == len(candidates_before) - 1
    assert candidate.id not in [x.id for x in election_list_after.candidates]


def test_add_pref_elec_candidate_mutation(db_session,
                                          client,
                                          logged_in_user,
                                          election_group_generator):
    """Test the add pref elec candidate mutation."""
    election_group = election_group_generator(
        owner=logged_in_user.person)
    election_list = election_group.elections[0].lists[0]
    candidates_before = {str(x.id): x for x in
                         election_list.candidates}
    variables = {
        'name': 'Foo Bare',
        'gender': 'female',
        'listId': str(election_list.id)
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
    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
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
            assert str(candidate.list_id) == variables['listId']
            assert candidate.meta['gender'] == variables['gender']
            break


def test_update_pref_elec_candidate_mutation(pref_candidates_foo,
                                             client, logged_in_user):
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
    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
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


def test_add_team_pref_elec_candidate_mutation(db_session,
                                               client,
                                               logged_in_user,
                                               election_group_generator):
    """Test the add pref elec candidate mutation."""
    election_group = election_group_generator(
        owner=logged_in_user.person,
        multiple=True
    )
    election_list = election_group.elections[0].lists[0]
    candidates_before = {str(x.id): x for x in
                         election_list.candidates}
    variables = {
        'name': 'Foo Bar',
        'coCandidates': [{'name': 'Bar Baz'}, {'name': 'Jane Doe'}],
        'listId': str(election_list.id)
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

    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
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
            assert str(candidate.list_id) == variables['listId']
            assert candidate.meta['co_candidates'] == variables['coCandidates']
            break


def test_update_team_pref_elec_candidate_mutation(
        team_pref_candidates_foo,
        client, logged_in_user):
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
    context = get_context()
    execution = client.execute(mutation, variables=variables, context=context)
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
    assert candidate_after.meta['co_candidates'] != (
        candidate_before.meta['coCandidates'])
    assert candidate_after.meta['co_candidates'] == variables['coCandidates']
