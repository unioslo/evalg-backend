import itertools
import pytest

from evalg.graphql import get_test_context, schema
from evalg.proc.pollbook import ElectionVoterPolicy
from evalg.proc.election import get_latest_election_group_count
from .utils.queries import queries
from .utils.register import RegisterOperationTestScenario

reg = RegisterOperationTestScenario()


def validate_person_return_data(response, is_allowed):

    # The id is always visible
    assert response['id']

    if is_allowed:
        assert response['displayName']
        assert response['lastUpdate']
        assert response['lastUpdateFromFeide']
        assert response['identifiers']
    else:
        assert not response['displayName']
        assert not response['lastUpdate']
        assert not response['lastUpdateFromFeide']
        assert not response['principal']
        assert not response['identifiers']


@reg.add_scenario('personForVoter', 'allow')
def test_auth_person_for_voter_in_my_election(
        client,
        db_session,
        election_group_generator,
        person_generator):
    """Test that we are allowed to lookup the person in owned election."""
    election_group = election_group_generator(owner=True)
    pollbook = election_group.elections[0].pollbooks[0]
    person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=False)
    variables = {'voterId': str(voter.id)}
    execution = client.execute(queries['personForVoter'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personForVoter']
    validate_person_return_data(response, True)


@reg.add_scenario('personForVoter', 'deny')
def test_auth_person_for_voter_not_in_my_election(
        client,
        db_session,
        election_group_generator,
        person_generator):
    """Test that we are not allowed to lookup the person for voter."""
    election_group = election_group_generator()
    pollbook = election_group.elections[0].pollbooks[0]
    person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=False)
    variables = {'voterId': str(voter.id)}
    execution = client.execute(queries['personForVoter'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personForVoter']
    validate_person_return_data(response, False)


def validate_voter_return_data(response, is_allowed):

    # The id is always visible
    assert response['id']

    if is_allowed:
        assert response['idType']
        assert response['idValue']
    else:
        assert not response['idType']
        assert not response['idValue']


@reg.add_scenario('votersForPerson', 'allow')
def test_auth_allow_voters_for_person_in_my_election(
        client,
        db_session,
        election_group_generator,
        person_generator):
    """Test that we are allowed to lookup the person in owned election."""
    election_group = election_group_generator(owner=True)
    pollbook = election_group.elections[0].pollbooks[0]
    person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter_policy.add_voter(pollbook, person, self_added=False)

    variables = {'id': str(person.id)}
    execution = client.execute(queries['votersForPerson'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['votersForPerson']
    assert len(response) == 1
    validate_voter_return_data(response[0], True)


@reg.add_scenario('votersForPerson', 'deny')
def test_auth_deny_voters_for_person_in_my_election(
        client,
        db_session,
        election_group_generator,
        person_generator):
    """Test that we are allowed to lookup the person in owned election."""
    election_group = election_group_generator(owner=True)
    pollbook = election_group.elections[0].pollbooks[0]
    person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter_policy.add_voter(pollbook, person, self_added=False)

    variables = {'id': str(person.id)}
    execution = client.execute(queries['votersForPerson'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['votersForPerson']
    assert len(response) == 1
    validate_voter_return_data(response[0], True)


@reg.add_scenario('viewer', 'allow')
def test_auth_viewer_logged_in(
        client,
        db_session,
        logged_in_user):
    """Test that we are allowed to lookup the viewer when logged inn."""
    execution = client.execute(queries['viewer'],
                               context=get_test_context(db_session))
    response = execution['data']['viewer']
    validate_person_return_data(response['person'], True)


@reg.add_scenario('viewer', 'deny')
def test_auth_viewer_not_logged_in(
        client,
        db_session):
    """Test that we are not allowed to lookup the view if not logged in."""
    execution = client.execute(queries['viewer'],
                               context=get_test_context(db_session))
    response = execution['data']['viewer']
    assert not response['person']


def validate_election_group_info(response, is_owner):
    assert response['id']
    if is_owner:
        assert response['name']
        assert response['type']
        assert response['publicKey']
    else:
        assert response['name']
        assert response['type']
        assert not response['publicKey']


@reg.add_scenario('electionGroup', 'allow')
def test_auth_election_group_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(owner=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroup'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroup']
    validate_election_group_info(response, True)


@reg.add_scenario('electionGroup', 'deny')
def test_auth_election_group_no_owned_not_published(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator()
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroup'],
                               variables=variables,
                               context=get_test_context(db_session))
    assert not execution['data']['electionGroup']


@reg.add_scenario('electionGroup', 'deny')
def test_auth_election_group_no_owned_published(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(running=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroup'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroup']
    validate_election_group_info(response, False)


@reg.add_scenario('electionGroupKeyMeta', 'allow')
def test_auth_election_group_key_meta_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        owner=True,
        running=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroupKeyMeta'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroupKeyMeta']

    assert response['generatedAt']
    validate_person_return_data(response['generatedBy'], True)


@reg.add_scenario('electionGroupKeyMeta', 'deny')
def test_auth_election_group_key_meta_not_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(running=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroupKeyMeta'],
                               variables=variables,
                               context=get_test_context(db_session))
    assert not execution['data']['electionGroupKeyMeta']


@reg.add_scenario('electionTemplate', 'allow')
@reg.add_scenario('electionTemplate', 'deny')
def test_auth_election_template(db_session, client):
    """
    Test auth for the electionTemplate query.

    Always allowed.
    """
    execution = client.execute(queries['electionTemplate'],
                               context=get_test_context(db_session))
    response = execution['data']['electionTemplate']
    assert response


@reg.add_scenario('masterKeys', 'allow')
@reg.add_scenario('masterKeys', 'deny')
def test_auth_master_keys(db_session, client, master_key):
    """
    Test auth for the masterKeys query.

    Always allowed.
    """
    private_key, master_key = master_key(db_session)
    execution = client.execute(queries['masterKeys'],
                               context=get_test_context(db_session))
    response = execution['data']['masterKeys']
    assert len(response) == 1
    assert response[0]['publicKey'] == master_key.public_key


@reg.add_scenario('electionGroupCountingResults', 'allow')
def test_auth_election_group_counting_results_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        owner=True,
        counted=True,
        multiple=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroupCountingResults'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroupCountingResults']
    assert len(response) == 1
    assert response[0]['id']
    assert response[0]['groupId']
    assert response[0]['initiatedAt']
    assert response[0]['finishedAt']
    assert response[0]['status']


@reg.add_scenario('electionGroupCountingResults', 'deny')
def test_auth_election_group_counting_results_not_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        counted=True,
        multiple=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroupCountingResults'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroupCountingResults']
    assert len(response) == 1
    assert response[0]['id']
    assert not response[0]['groupId']
    assert not response[0]['initiatedAt']
    assert not response[0]['finishedAt']
    assert not response[0]['status']


@reg.add_scenario('electionGroupCount', 'allow')
def test_auth_election_group_count_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        owner=True,
        multiple=True,
        counted=True)
    count = get_latest_election_group_count(
        db_session, election_group.id)
    variables = {'id': str(count.id)}
    execution = client.execute(queries['electionGroupCount'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroupCount']
    assert response['id']
    assert response['groupId']
    assert response['initiatedAt']
    assert response['finishedAt']
    assert response['status']


@reg.add_scenario('electionGroupCount', 'deny')
def test_auth_election_group_count_not_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        multiple=True,
        counted=True)
    count = get_latest_election_group_count(
        db_session, election_group.id)
    variables = {'id': str(count.id)}
    execution = client.execute(queries['electionGroupCount'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroupCount']
    assert response['id']
    assert not response['groupId']
    assert not response['initiatedAt']
    assert not response['finishedAt']
    assert not response['status']


@reg.add_scenario('searchVoters', 'allow')
def test_auth_search_voters_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        owner=True,
        running=True)
    voter = election_group.elections[0].pollbooks[0].voters[0]
    variables = {
        'electionGroupId': str(election_group.id),
        'search': voter.id_value
    }
    execution = client.execute(queries['searchVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['searchVoters']
    assert len(response) == 1
    assert response[0]['id']
    assert response[0]['idValue'] == voter.id_value
    assert response[0]['idType'] == voter.id_type


@reg.add_scenario('searchVoters', 'deny')
def test_auth_search_voters_not_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(running=True)
    voter = election_group.elections[0].pollbooks[0].voters[0]
    variables = {
        'electionGroupId': str(election_group.id),
        'search': voter.id_value
    }
    execution = client.execute(queries['searchVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    assert execution['data']['searchVoters'] == [None]


@reg.add_scenario('electionResult', 'allow')
def test_auth_election_result_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        owner=True,
        counted=True,
        multiple=True)
    count = get_latest_election_group_count(
        db_session, election_group.id)
    election_result = count.election_results[0]
    variables = {'id': str(election_result.id)}
    execution = client.execute(queries['electionResult'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionResult']
    assert response['id']
    assert response['electionProtocol']
    assert len(response['ballots']) == 0
    assert response['electionId']
    assert response['electionGroupCountId']
    assert response['result']
    assert response['pollbookStats']
    assert response['ballotsWithMetadata']


@reg.add_scenario('electionResult', 'deny')
def test_auth_election_result_not_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(
        counted=True,
        multiple=True)
    count = get_latest_election_group_count(
        db_session, election_group.id)
    election_result = count.election_results[0]
    variables = {'id': str(election_result.id)}
    execution = client.execute(queries['electionResult'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionResult']
    assert response['id']
    assert not response['electionProtocol']
    assert not response['ballots']
    assert not response['electionId']
    assert not response['electionGroupCountId']
    assert not response['result']
    assert not response['pollbookStats']
    assert not response['ballotsWithMetadata']


@reg.add_scenario('personsWithMultipleVerifiedVoters', 'allow')
def test_auth_person_with_multiple_verified_voters_owned(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(owner=True,
                                              running=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['personsWithMultipleVerifiedVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personsWithMultipleVerifiedVoters']
    assert len(response) == 0


@reg.add_scenario('personsWithMultipleVerifiedVoters', 'deny')
def test_auth_person_with_multiple_verified_voters_deny(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    election_group = election_group_generator(running=True)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['personsWithMultipleVerifiedVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personsWithMultipleVerifiedVoters']
    assert not response


@reg.add_scenario('electionGroups', 'allow')
@reg.add_scenario('electionGroups', 'deny')
def test_auth_election_groups_votable(
        db_session,
        client,
        election_group_generator):
    """Test auth for the electionGroup query."""
    # Visible
    election_group_generator(running=True)

    # Not visible
    election_group_generator()
    execution = client.execute(queries['electionGroups'],
                               context=get_test_context(db_session))
    print(execution)
    response = execution['data']['electionGroups']
    assert len(response) == 1


@pytest.mark.parametrize(
    'query,scenario',
    list(itertools.product(
        list(schema.get_query_type().fields.keys()), ['allow', 'deny'])))
def test_query_test_coverage(query, scenario):
    assert reg.operations_test_exist_for_scenario(query, scenario), (
        "Missing test scenario {} for mutation {}".format(scenario, query))
