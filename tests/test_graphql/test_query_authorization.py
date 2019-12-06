

#    election_groups
#    persons_with_multiple_verified_voters
#    election_template
#
#    election_group_count
#    election_group_counting_results
#    election_result
#
#    voters_for_person
#    search_voters
#    search_groups

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


@pytest.mark.test
@reg.add_scenario('personForVoter', 'allow')
def test_auth_person_for_voter_in_my_election(
        client,
        db_session,
        logged_in_user,
        owned_election_group,
        simple_person):
    """Test that we are allowed to lookup the person in owned election."""
    election_group = owned_election_group(db_session, logged_in_user.person)
    pollbook = election_group.elections[0].pollbooks[0]
    person = simple_person(db_session)
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=False)
    variables = {'voterId': str(voter.id)}
    execution = client.execute(queries['personForVoter'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personForVoter']
    validate_person_return_data(response, True)


@pytest.mark.test
@reg.add_scenario('personForVoter', 'deny')
def test_auth_person_for_voter_not_in_my_election(
        client,
        db_session,
        logged_in_user,
        simple_election_group,
        simple_person):
    """Test that we are not allowed to lookup the person for voter."""
    election_group = simple_election_group(db_session)
    pollbook = election_group.elections[0].pollbooks[0]
    person = simple_person(db_session)
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


@pytest.mark.test
@reg.add_scenario('votersForPerson', 'allow')
def test_auth_voters_for_person_in_my_election(
        client,
        db_session,
        logged_in_user,
        owned_election_group,
        simple_person):
    """Test that we are allowed to lookup the person in owned election."""
    election_group = owned_election_group(db_session, logged_in_user.person)
    pollbook = election_group.elections[0].pollbooks[0]
    person = simple_person(db_session)
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=False)

    variables = {'id': str(person.id)}
    execution = client.execute(queries['votersForPerson'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['votersForPerson']
    assert len(response) == 1
    validate_voter_return_data(response[0], True)


@pytest.mark.test
@reg.add_scenario('votersForPerson', 'deny')
def test_auth_voters_for_person_in_my_election(
        client,
        db_session,
        logged_in_user,
        owned_election_group,
        simple_person):
    """Test that we are allowed to lookup the person in owned election."""
    election_group = owned_election_group(db_session, logged_in_user.person)
    pollbook = election_group.elections[0].pollbooks[0]
    person = simple_person(db_session)
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=False)

    variables = {'id': str(person.id)}
    execution = client.execute(queries['votersForPerson'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['votersForPerson']
    assert len(response) == 1
    validate_voter_return_data(response[0], True)


@pytest.mark.test
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


@pytest.mark.test
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


@pytest.mark.test
@reg.add_scenario('electionGroup', 'allow')
def test_auth_election_group_owned(
        db_session,
        client,
        logged_in_user,
        owned_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_election_group(db_session, logged_in_user.person)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroup'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroup']
    validate_election_group_info(response, True)


@pytest.mark.test
@reg.add_scenario('electionGroup', 'deny')
def test_auth_election_group_no_owned_not_published(
        db_session,
        client,
        logged_in_user,
        simple_election_group):
    """Test auth for the electionGroup query."""
    election_group = simple_election_group(db_session)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroup'],
                               variables=variables,
                               context=get_test_context(db_session))
    assert not execution['data']['electionGroup']


@pytest.mark.test
@reg.add_scenario('electionGroup', 'deny')
def test_auth_election_group_no_owned_published(
        db_session,
        client,
        logged_in_user,
        votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = votable_election_group(db_session)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroup'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroup']
    validate_election_group_info(response, False)


@pytest.mark.test
@reg.add_scenario('electionGroupKeyMeta', 'allow')
def test_auth_election_group_key_meta_owned(
        db_session,
        client,
        logged_in_user,
        owned_votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_votable_election_group(db_session,
                                                  logged_in_user.person)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroupKeyMeta'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['electionGroupKeyMeta']

    assert response['generatedAt']
    validate_person_return_data(response['generatedBy'], True)


@pytest.mark.test
@reg.add_scenario('electionGroupKeyMeta', 'deny')
def test_auth_election_group_key_meta_not_owned(
        db_session,
        client,
        logged_in_user,
        votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = votable_election_group(db_session)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['electionGroupKeyMeta'],
                               variables=variables,
                               context=get_test_context(db_session))
    assert not execution['data']['electionGroupKeyMeta']


@pytest.mark.test
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


@pytest.mark.test
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


@pytest.mark.test
@reg.add_scenario('electionGroupCountingResults', 'allow')
def test_auth_election_group_counting_results_owned(
        db_session,
        client,
        logged_in_user,
        owned_counted_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_counted_election_group(
        db_session,
        logged_in_user.person)
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


@pytest.mark.test
@reg.add_scenario('electionGroupCountingResults', 'deny')
def test_auth_election_group_counting_results_not_owned(
        db_session,
        client,
        logged_in_user,
        counted_election_group):
    """Test auth for the electionGroup query."""
    election_group = counted_election_group(db_session)
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


@pytest.mark.test
@reg.add_scenario('electionGroupCount', 'allow')
def test_auth_election_group_count_owned(
        db_session,
        client,
        logged_in_user,
        owned_counted_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_counted_election_group(
        db_session,
        logged_in_user.person)
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


@pytest.mark.test
@reg.add_scenario('electionGroupCount', 'deny')
def test_auth_election_group_count_not_owned(
        db_session,
        client,
        logged_in_user,
        counted_election_group):
    """Test auth for the electionGroup query."""
    election_group = counted_election_group(db_session)
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


@pytest.mark.test
@reg.add_scenario('searchVoters', 'allow')
def test_auth_search_voters_owned(
        db_session,
        client,
        logged_in_user,
        owned_votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_votable_election_group(db_session,
                                                  logged_in_user.person)
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


@pytest.mark.test
@reg.add_scenario('searchVoters', 'deny')
def test_auth_search_voters_not_owned(
        db_session,
        client,
        logged_in_user,
        votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = votable_election_group(db_session)

    voter = election_group.elections[0].pollbooks[0].voters[0]
    variables = {
        'electionGroupId': str(election_group.id),
        'search': voter.id_value
    }
    execution = client.execute(queries['searchVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    assert execution['data']['searchVoters'] == [None]


@pytest.mark.test
@reg.add_scenario('electionResult', 'allow')
def test_auth_election_result_owned(
        db_session,
        client,
        logged_in_user,
        owned_counted_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_counted_election_group(
        db_session,
        logged_in_user.person)
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


@pytest.mark.test
@reg.add_scenario('electionResult', 'deny')
def test_auth_election_result_not_owned(
        db_session,
        client,
        logged_in_user,
        counted_election_group):
    """Test auth for the electionGroup query."""
    election_group = counted_election_group(db_session)
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


@pytest.mark.test
@reg.add_scenario('personsWithMultipleVerifiedVoters', 'allow')
def test_auth_person_with_multiple_verified_voters_owned(
        db_session,
        client,
        logged_in_user,
        owned_votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = owned_votable_election_group(db_session,
                                                  logged_in_user.person)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['personsWithMultipleVerifiedVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personsWithMultipleVerifiedVoters']
    assert len(response) == 0


@pytest.mark.test
@reg.add_scenario('personsWithMultipleVerifiedVoters', 'deny')
def test_auth_person_with_multiple_verified_voters_deny(
        db_session,
        client,
        logged_in_user,
        votable_election_group):
    """Test auth for the electionGroup query."""
    election_group = votable_election_group(db_session)
    variables = {'id': str(election_group.id)}
    execution = client.execute(queries['personsWithMultipleVerifiedVoters'],
                               variables=variables,
                               context=get_test_context(db_session))
    response = execution['data']['personsWithMultipleVerifiedVoters']
    assert not response


@pytest.mark.test
@reg.add_scenario('electionGroups', 'allow')
@reg.add_scenario('electionGroups', 'deny')
def test_auth_election_groups_votable(
        db_session,
        client,
        logged_in_user,
        simple_election_group,
        votable_election_group):
    """Test auth for the electionGroup query."""
    # Visible
    votable_election_group(db_session)
    # Not visible
    simple_election_group(db_session)
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
