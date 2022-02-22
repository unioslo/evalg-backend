"""Test authorization for mutations."""

import datetime
import itertools
import json

import pytest

from evalg.graphql import schema, get_test_context
from .utils.register import RegisterOperationTestScenario


reg = RegisterOperationTestScenario()


@reg.add_scenario('createNewElectionGroup', 'allow')
@reg.add_scenario('createNewElectionGroup', 'deny')
def test_allow_create_new_election_group(db_session,
                                         ou_generator,
                                         client,
                                         logged_in_user):
    """
    Allow and deny scenario of createNewElectionGroup.

    This mutations is always allowed so no need to test denying.
    We need to include the logged_in_user fixture to have a user to run the
    mutation.
    """
    ou = ou_generator()
    variables = {
        'ouId': str(ou.id),
        'template': True,
        'templateName': 'uio_dean',
        'name': None
    }
    mutation = """
    mutation ($ouId: UUID!,
              $template: Boolean!,
              $templateName: String!,
              $name: ElectionName) {
        createNewElectionGroup(ouId: $ouId,
                               template: $template,
                               templateName: $templateName,
                               nameDict: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['createNewElectionGroup']
    assert response['ok']


@reg.add_scenario('updateBaseSettings', 'allow')
@reg.add_scenario('updateBaseSettings', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_base_settings(db_session,
                                   is_owner,
                                   is_allowed,
                                   client,
                                   election_group_generator):
    """Allowed and denied scenario tests of updateBaseSettings."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    elections = [{'id': str(e.id),
                  'seats': e.meta['candidate_rules']['seats'],
                  'substitutes': e.meta['candidate_rules']['substitutes'],
                  'active': e.active}
                 for e in election_group.elections]
    new_gender_quota = not election_group.meta['candidate_rules'][
        'candidate_gender']
    variables = {
        'id': str(election_group.id),
        'hasGenderQuota': new_gender_quota,
        'elections': elections,
    }
    mutation = """
    mutation ($id: UUID!,
              $hasGenderQuota: Boolean!,
              $elections: [ElectionBaseSettingsInput]!) {
        updateBaseSettings(id: $id,
                           hasGenderQuota: $hasGenderQuota,
                           elections: $elections) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateBaseSettings']
    assert response['ok'] == is_allowed


@reg.add_scenario('updateElectionGroupName', 'allow')
@reg.add_scenario('updateElectionGroupName', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_base_settings(db_session,
                                   is_owner,
                                   is_allowed,
                                   client,
                                   election_group_generator):
    """Allowed and denied scenario tests of updateBaseSettings."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    elections = [{'id': str(e.id),
                  'seats': e.meta['candidate_rules']['seats'],
                  'substitutes': e.meta['candidate_rules']['substitutes'],
                  'active': e.active}
                 for e in election_group.elections]
    variables = {
        'id': str(election_group.id),
        'name': election_group.name
    }
    mutation = """
    mutation ($id: UUID!,
              $name: ElectionName!) {
        updateElectionGroupName(electionGroupId: $id,
                                nameDict: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateElectionGroupName']
    assert response['ok'] == is_allowed


@reg.add_scenario('publishElectionGroup', 'allow')
@reg.add_scenario('publishElectionGroup', 'deny')
@pytest.mark.parametrize(
    'is_owner, is_publisher, is_allowed',
    [(True, True, True),
     (True, False, False),
     (False, True, False),
     (False, False, False)])
def test_auth_publish_election_group(db_session,
                                     is_owner,
                                     is_publisher,
                                     is_allowed,
                                     client,
                                     logged_in_user,
                                     election_group_generator,
                                     make_person_publisher):
    """Allowed and denied scenario of publishElectionGroup."""
    election_group = election_group_generator(owner=is_owner)
    if is_publisher:
        make_person_publisher(db_session, logged_in_user.person)
    variables = {'id': str(election_group.id)}
    mutation = """
    mutation ($id: UUID!) {
        publishElectionGroup(id: $id) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    result = execution['data']['publishElectionGroup']
    assert result['success'] == is_allowed
    if not is_allowed:
        assert result['code'] == 'permission-denied'


@reg.add_scenario('unpublishElectionGroup', 'allow')
@reg.add_scenario('unpublishElectionGroup', 'deny')
@pytest.mark.parametrize(
    'is_owner, is_publisher, is_allowed',
    [(True, True, True),
     (True, False, False),
     (False, True, False),
     (False, False, False)])
def test_auth_unpublish_election_group(db_session,
                                       is_owner,
                                       is_publisher,
                                       is_allowed,
                                       client,
                                       logged_in_user,
                                       election_group_generator,
                                       make_person_publisher):
    """Allowed and denied scenario of unpublishElectionGroup."""
    election_group = election_group_generator(owner=is_owner)
    if is_publisher:
        make_person_publisher(db_session, logged_in_user.person)
    variables = {'id': str(election_group.id)}
    mutation = """
    mutation ($id: UUID!) {
        unpublishElectionGroup(id: $id) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    result = execution['data']['unpublishElectionGroup']
    assert result['success'] == is_allowed
    if not is_allowed:
        assert result['code'] == 'permission-denied'


@reg.add_scenario('setElectionGroupKey', 'allow')
@reg.add_scenario('setElectionGroupKey', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_set_election_group_key(db_session,
                                     is_owner,
                                     is_allowed,
                                     client,
                                     election_keys,
                                     election_group_generator):
    """Allowed and denied scenario tests of setElectionGroupKey."""
    election_group = election_group_generator(owner=is_owner)
    variables = {
        'id': str(election_group.id),
        'publicKey': election_keys['public']
    }
    mutation = """
    mutation ($id: UUID!, $publicKey: String!) {
        setElectionGroupKey(id: $id, publicKey: $publicKey) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['setElectionGroupKey']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('startElectionGroupCount', 'allow')
@reg.add_scenario('startElectionGroupCount', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_start_election_group_count(db_session,
                                         is_owner,
                                         is_allowed,
                                         client,
                                         election_keys,
                                         election_group_generator):
    """Allowed and denied scenario tests of startElectionGroupCount."""
    election_group = election_group_generator(
        owner=is_owner,
        countable=True,
        multiple=True)
    variables = {
        'id': str(election_group.id),
        'electionKey': election_keys['private']
    }
    mutation = """
        mutation startElectionGroupCount($id: UUID!, $electionKey: String!) {
            startElectionGroupCount(id: $id, electionKey: $electionKey) {
                success
                code
            }
        }
        """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['startElectionGroupCount']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('updateVotingPeriods', 'allow')
@reg.add_scenario('updateVotingPeriods', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_update_voting_periods(db_session,
                                    is_owner,
                                    is_allowed,
                                    client,
                                    election_group_generator):
    """Allowed and denied scenario tests of updateVotingPeriods."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    elections = [{'id': str(e.id),
                  'start': str(e.start - datetime.timedelta(days=3)),
                  'end': str(e.end)}
                 for e in election_group.elections]
    variables = {'hasMultipleTimes': False, 'elections': elections}
    mutation = """
    mutation ($hasMultipleTimes: Boolean!,
              $elections: [ElectionVotingPeriodInput]!) {
        updateVotingPeriods(hasMultipleTimes: $hasMultipleTimes,
                            elections: $elections) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateVotingPeriods']
    assert response['ok'] == is_allowed


@reg.add_scenario('updateVoterInfo', 'allow')
@reg.add_scenario('updateVoterInfo', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_update_voter_info(db_session,
                                is_owner,
                                is_allowed,
                                client,
                                election_group_generator):
    """Allowed and denied scenario tests of updateVoterInfo."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    elections = [{'id': str(e.id),
                  'mandatePeriodStart': str(e.mandate_period_start),
                  'mandatePeriodEnd': str(e.mandate_period_end +
                                          datetime.timedelta(days=3))}
                 for e in election_group.elections]
    variables = {'elections': elections}
    mutation = """
    mutation ($elections: [ElectionVoterInfoInput]!) {
        updateVoterInfo(elections: $elections) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateVoterInfo']
    assert response['ok'] == is_allowed


@reg.add_scenario('addElectionList', 'allow')
@reg.add_scenario('addElectionList', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_add_election_list(db_session,
                                is_owner,
                                is_allowed,
                                client,
                                election_group_generator):
    """Allowed and denied scenario tests of addElectionList."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)

    election = election_group.elections[0]
    variables = {
        'name': {
            'nb': 'test',
            'nn': 'test',
            'en': 'test'
        },
        'electionId': str(election.id)
    }
    mutation = """
    mutation ($name: LangDict!, $electionId: UUID!) {
        addElectionList(name: $name, electionId: $electionId) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addElectionList']
    assert response['ok'] == is_allowed


@reg.add_scenario('updateElectionList', 'allow')
@reg.add_scenario('updateElectionList', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_election_list(db_session,
                                   is_owner,
                                   is_allowed,
                                   client,
                                   election_group_generator):
    """Allowed and denied scenario tests of updateElectionList."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)

    election = election_group.elections[0]
    election_list = election_group.elections[0].lists[0]
    variables = {
        'id': str(election_list.id),
        'name': {
            'nb': 'test',
            'nn': 'test',
            'en': 'test'
        },
        'electionId': str(election.id)
    }
    mutation = """
    mutation ($id: UUID!, $name: LangDict!, $electionId: UUID!) {
        updateElectionList(id: $id, name: $name, electionId: $electionId) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateElectionList']
    assert response['ok'] == is_allowed


@reg.add_scenario('deleteElectionList', 'allow')
@reg.add_scenario('deleteElectionList', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_delete_election_list(db_session,
                                   is_owner,
                                   is_allowed,
                                   client,
                                   election_group_generator):
    """Allowed and denied scenario tests of updateElectionList."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    election_list = election_group.elections[0].lists[0]
    variables = {
        'id': str(election_list.id)
    }
    mutation = """
    mutation ($id: UUID!) {
        deleteElectionList(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['deleteElectionList']
    assert response['ok'] == is_allowed


@reg.add_scenario('updateListElecCandidate', 'allow')
@reg.add_scenario('updateListElecCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_list_elec_candidate(
    db_session,
    is_owner,
    is_allowed,
    client,
    election_group_generator
) -> None:
    """Allowed and denied scenario tests of updatePrefElecCandidate."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    election_list = election_group.elections[0].lists[0]
    candidate = election_group.elections[0].lists[0].candidates[0]
    new_name = '{} Testesen'.format(candidate.name)
    variables = {
        'id': str(candidate.id),
        'name': new_name,
        'listId': str(election_list.id),
        'priority': 0,
        'preCumulated': True
    }
    mutation = """
    mutation (
        $listId: UUID!,
        $id: UUID!,
        $name: String!,
        $priority: Int!,
        $preCumulated: Boolean!
    ) {
        updateListElecCandidate(
            listId: $listId,
            id: $id,
            name: $name,
            preCumulated: $preCumulated,
            priority: $priority
        ) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateListElecCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('addListElecCandidate', 'allow')
@reg.add_scenario('addListElecCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_add_list_elec_candidate(
    db_session,
    is_owner,
    is_allowed,
    client,
    election_group_generator
) -> None:
    """Allowed and denied scenario tests of updatePrefElecCandidate."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    election_list = election_group.elections[0].lists[0]
    variables = {
        'name': "Test Testesen",
        'listId': str(election_list.id),
        'priority': 1,
        'preCumulated': False
    }
    mutation = """
    mutation (
        $listId: UUID!,
        $name: String!,
        $priority: Int!,
        $preCumulated: Boolean!
    ) {
        addListElecCandidate(
            listId: $listId,
            name: $name,
            preCumulated: $preCumulated,
            priority: $priority
        ) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addListElecCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('updatePrefElecCandidate', 'allow')
@reg.add_scenario('updatePrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_pref_elec_candidate(db_session,
                                         is_owner,
                                         is_allowed,
                                         client,
                                         election_group_generator):
    """Allowed and denied scenario tests of updatePrefElecCandidate."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    election_list = election_group.elections[0].lists[0]
    candidate = election_group.elections[0].lists[0].candidates[0]
    new_name = '{} Testesen'.format(candidate.name)
    variables = {
        'gender': candidate.meta['gender'],
        'listId': str(election_list.id),
        'id': str(candidate.id),
        'name': new_name
    }
    mutation = """
    mutation ($gender: String!, $listId: UUID!, $id: UUID!, $name: String!) {
        updatePrefElecCandidate(gender: $gender,
                                listId: $listId,
                                id: $id,
                                name: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updatePrefElecCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('addPrefElecCandidate', 'allow')
@reg.add_scenario('addPrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_add_pref_elec_candidate(db_session,
                                      is_owner,
                                      is_allowed,
                                      client,
                                      election_group_generator):
    """Allowed and denied scenario tests of addPrefElecCandidate."""
    election_group = election_group_generator(
        owner=is_owner,
        multiple=True)
    election_list = election_group.elections[0].lists[0]
    variables = {
        'gender': 'female',
        'listId': str(election_list.id),
        'name': 'Test Testesen'
    }
    mutation = """
    mutation ($gender: String!, $listId: UUID!, $name: String!) {
        addPrefElecCandidate(gender: $gender, listId: $listId , name: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addPrefElecCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('updateTeamPrefElecCandidate', 'allow')
@reg.add_scenario('updateTeamPrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_team_pref_elec_candidate(db_session,
                                              is_owner,
                                              is_allowed,
                                              client,
                                              election_group_generator):
    """Allowed and denied scenario tests of updatePrefElecCandidate."""
    election_group = election_group_generator(owner=is_owner)
    election_list = election_group.elections[0].lists[0]
    candidate = election_group.elections[0].lists[0].candidates[0]
    new_name = '{} Testesen'.format(candidate.name)
    variables = {
        'coCandidates': candidate.meta['co_candidates'],
        'listId': str(election_list.id),
        'id': str(candidate.id),
        'name': new_name
    }
    mutation = """
    mutation ($coCandidates: [CoCandidatesInput]!,
              $listId: UUID!,
              $id: UUID!,
              $name: String!) {
        updateTeamPrefElecCandidate(coCandidates: $coCandidates,
                                    listId: $listId,
                                    id: $id,
                                    name: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateTeamPrefElecCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('addTeamPrefElecCandidate', 'allow')
@reg.add_scenario('addTeamPrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_add_team_pref_elec_candidate(db_session,
                                           is_owner,
                                           is_allowed,
                                           client,
                                           election_group_generator):
    """Allowed and denied scenario tests of addTeamPrefElecCandidate."""
    election_group = election_group_generator(owner=is_owner)
    election_list = election_group.elections[0].lists[0]
    variables = {
        'coCandidates': [{'name': 'Test Testemeresen'}],
        'listId': str(election_list.id),
        'name': 'Test Testesen'
    }
    mutation = """
    mutation ($coCandidates: [CoCandidatesInput]!,
              $listId: UUID!,
              $name: String!) {
        addTeamPrefElecCandidate(coCandidates: $coCandidates,
                                 listId: $listId ,
                                 name: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addTeamPrefElecCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('deleteCandidate', 'allow')
@reg.add_scenario('deleteCandidate', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_delete_candidate(db_session,
                               is_owner,
                               is_allowed,
                               client,
                               election_group_generator):
    """Allowed and denied scenario tests of deleteCandidate."""
    election_group = election_group_generator(owner=is_owner)
    candidate = election_group.elections[0].candidates[0]
    variables = {'id': str(candidate.id)}
    mutation = """
    mutation ($id: UUID!) {
        deleteCandidate(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['deleteCandidate']
    assert response['ok'] == is_allowed


@reg.add_scenario('addVoterByPersonId', 'allow')
@reg.add_scenario('addVoterByPersonId', 'deny')
@pytest.mark.parametrize(
    "is_owner,is_allowed", [(True, True,), (False, False)])
def test_auth_add_voter_by_person_id(db_session,
                                     is_owner,
                                     is_allowed,
                                     client,
                                     person_generator,
                                     election_group_generator):
    """Allowed and denied scenario tests of addVoterByPersonId."""
    election_group = election_group_generator(owner=is_owner)
    pollbook = election_group.elections[0].pollbooks[0]
    variables = {
        'personId': str(person_generator().id),
        'pollbookId': str(pollbook.id)
    }
    mutation = """
    mutation ($personId: UUID!, $pollbookId: UUID!) {
        addVoterByPersonId(personId: $personId, pollbookId: $pollbookId) {
            id
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addVoterByPersonId']
    assert (response is not None) == is_allowed


@reg.add_scenario('addVoterByIdentifier', 'allow')
@reg.add_scenario('addVoterByIdentifier', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_add_voter_by_identifier(db_session,
                                      is_owner,
                                      is_allowed,
                                      client,
                                      person_generator,
                                      election_group_generator):
    """Allowed and denied scenario tests of addVoterByIdentifier."""
    election_group = election_group_generator(owner=is_owner)
    pollbook = election_group.elections[0].pollbooks[0]
    feide_id = next(i for i in person_generator().identifiers if
                    i.id_type == 'feide_id')
    variables = {
        'idType': feide_id.id_type,
        'idValue': feide_id.id_value,
        'pollbookId': str(pollbook.id)
    }
    mutation = """
    mutation ($idType: PersonIdType!, $idValue: String!, $pollbookId: UUID!) {
        addVoterByIdentifier(idType: $idType,
                             idValue: $idValue,
                             pollbookId: $pollbookId) {
            id
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addVoterByIdentifier']
    assert (response is not None) == is_allowed


@reg.add_scenario('updateVoterPollbook', 'allow')
@reg.add_scenario('updateVoterPollbook', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_update_voter_pollbook(db_session,
                                    is_owner,
                                    is_allowed,
                                    client,
                                    election_group_generator):
    """Allowed and denied scenario tests of updateVoterPollbook."""
    election_group = election_group_generator(owner=is_owner)
    pollbook_1 = election_group.elections[0].pollbooks[0]
    pollbook_2 = election_group.elections[0].pollbooks[1]
    voter = next(x for x in pollbook_1.voters if not x.self_added)
    variables = {'id': str(voter.id), 'pollbookId': str(pollbook_2.id)}
    mutation = """
    mutation ($id: UUID!, $pollbookId: UUID!) {
        updateVoterPollbook(id: $id, pollbookId: $pollbookId) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateVoterPollbook']
    assert response['ok'] == is_allowed


@reg.add_scenario('updateVoterReason', 'allow')
@reg.add_scenario('updateVoterReason', 'deny')
@pytest.mark.parametrize(
    "as_logged_in_user,is_allowed", [(True, True), (False, False)])
def test_update_voter_reason(db_session,
                             as_logged_in_user,
                             is_allowed,
                             client,
                             logged_in_user,
                             election_group_generator,):
    """Allow and deny scenarios for updateVoterReason."""
    election_group = election_group_generator(
        running=True,
        logged_in_user_in_census=True)
    pollbook = election_group.elections[0].pollbooks[0]
    logged_in_feide_id = next(x.id_value for x in
                              logged_in_user.person.identifiers if
                              x.id_type == 'feide_id')
    if as_logged_in_user:
        voter = next(x for x in pollbook.voters if
                     x.id_value == logged_in_feide_id)
    else:
        voter = next(x for x in pollbook.voters if
                     x.id_value != logged_in_feide_id)
    variables = {'id': str(voter.id), 'reason': 'Test 123'}
    mutation = """
    mutation ($id: UUID!, $reason: String!) {
        updateVoterReason(id: $id, reason: $reason) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['updateVoterReason']
    assert response['ok'] == is_allowed


@reg.add_scenario('deleteVoter', 'allow')
@reg.add_scenario('deleteVoter', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_delete_voter(db_session,
                           is_owner,
                           is_allowed,
                           client,
                           election_group_generator):
    """Allow and deny scenarios for deleteVoter."""
    election_group = election_group_generator(owner=is_owner)
    voters = election_group.elections[0].pollbooks[0].voters
    voter = next(x for x in voters if not x.self_added)
    variables = {'id': str(voter.id)}
    mutation = """
    mutation ($id: UUID!) {
        deleteVoter(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['deleteVoter']
    assert response['ok'] == is_allowed


@reg.add_scenario('deleteVotersInPollbook', 'allow')
@reg.add_scenario('deleteVotersInPollbook', 'deny')
@pytest.mark.parametrize(
    "is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_delete_voters_in_pollbook(db_session,
                                        is_owner,
                                        is_allowed,
                                        client,
                                        election_group_generator):
    """Allow and deny scenarios for deleteVotersInPollbook."""
    election_group = election_group_generator(owner=is_owner)
    pollbook = election_group.elections[0].pollbooks[0]
    variables = {'id': str(pollbook.id)}
    mutation = """
    mutation ($id: UUID!) {
        deleteVotersInPollbook(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['deleteVotersInPollbook']
    assert response['ok'] == is_allowed


@reg.add_scenario('uploadCensusFile', 'allow')
@reg.add_scenario('uploadCensusFile', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_upload_census_file(db_session,
                                 is_owner,
                                 is_allowed,
                                 client,
                                 election_group_generator,
                                 feide_id_plane_text_census_builder,
                                 celery_app,
                                 monkeypatch):
    """Allow and deny scenarios for uploadCensusFile."""
    # Mokeypatch away the celery job.
    monkeypatch.setattr(
        'evalg.tasks.flask_celery.make_celery', lambda a: celery_app)
    monkeypatch.setattr(
        'evalg.tasks.celery_worker.import_census_file_task.delay',
        lambda x, y: f"Patched {x}-{y}")

    election_group = election_group_generator(owner=is_owner)
    pollbook = election_group.elections[0].pollbooks[0]
    variables = {
        'censusFile': feide_id_plane_text_census_builder.files['file'],
        'pollbookId': str(pollbook.id)
    }
    mutation = """
    mutation ($censusFile: Upload!, $pollbookId: UUID!) {
        uploadCensusFile(censusFile: $censusFile, pollbookId: $pollbookId) {
            success
            code
            numFailed
            numOk
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['uploadCensusFile']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('reviewVoter', 'allow')
@reg.add_scenario('reviewVoter', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_review_voter(db_session,
                           is_owner,
                           is_allowed,
                           client,
                           election_group_generator):
    """Allow and deny scenarios for reviewVoter."""
    election_group = election_group_generator(
        owner=is_owner,
        with_self_added_voters=True)
    pollbook = election_group.elections[0].pollbooks[0]
    voter = next(x for x in pollbook.voters if x.self_added)
    variables = {'id': str(voter.id), 'verify': True}
    mutation = """
    mutation ($id: UUID!, $verify: Boolean!) {
        reviewVoter(id: $id, verify: $verify) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['reviewVoter']
    assert response['ok'] == is_allowed


@reg.add_scenario('undoReviewVoter', 'allow')
@reg.add_scenario('undoReviewVoter', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_undo_review_voter(db_session,
                                is_owner,
                                is_allowed,
                                client,
                                election_group_generator):
    """Allow and deny scenarios for undoReviewVoter."""
    election_group = election_group_generator(
        owner=is_owner,
        with_self_added_voters=True)
    pollbook = election_group.elections[0].pollbooks[0]
    voter = next(x for x in pollbook.voters if x.self_added)
    variables = {'id': str(voter.id)}
    mutation = """
    mutation ($id: UUID!) {
        undoReviewVoter(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['undoReviewVoter']
    assert response['ok'] == is_allowed


@reg.add_scenario('addElectionGroupRoleByIdentifier', 'allow')
@reg.add_scenario('addElectionGroupRoleByIdentifier', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_add_election_group_role_by_identifier(db_session,
                                                    is_owner,
                                                    is_allowed,
                                                    client,
                                                    election_group_generator,
                                                    logged_in_user):
    """Allow and deny scenarios for addElectionGroupRoleByIdentifier."""
    election_group = election_group_generator(owner=is_owner)
    person = logged_in_user.person
    feide_id = next(i for i in person.identifiers if i.id_type == 'feide_id')
    variables = {
        'electionGroupId': str(election_group.id),
        'idType': feide_id.id_type,
        'idValue': feide_id.id_value,
        'role': 'admin'
    }
    mutation = """
    mutation ($electionGroupId: UUID!,
              $idType: PersonIdType!,
              $idValue: String!,
              $role: ElectionGroupRoleType!) {
        addElectionGroupRoleByIdentifier(electionGroupId: $electionGroupId,
                                         idType: $idType,
                                         idValue: $idValue,
                                         role: $role) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addElectionGroupRoleByIdentifier']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('removeElectionGroupRoleByGrant', 'allow')
@reg.add_scenario('removeElectionGroupRoleByGrant', 'deny')
@pytest.mark.parametrize('is_owner,is_allowed', [(True, True), (False, False)])
def test_auth_remove_election_group_role_by_grant(
        db_session,
        is_owner,
        is_allowed,
        client,
        election_group_grant_generator):
    """Allow and deny scenarios for removeElectionGroupRoleByGrant."""
    grant = election_group_grant_generator(owner=is_owner)
    variables = {'grantId': str(grant.grant_id)}
    mutation = """
    mutation ($grantId: UUID!) {
        removeElectionGroupRoleByGrant(grantId: $grantId) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['removeElectionGroupRoleByGrant']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('vote', 'allow')
@reg.add_scenario('vote', 'deny')
@pytest.mark.parametrize(
    "is_owner,as_logged_in_user,is_allowed",
    [(True, True, True),
     (False, True, True),
     (True, False, False),
     (False, False, False)])
def test_auth_vote(db_session,
                   is_owner,
                   as_logged_in_user,
                   is_allowed,
                   client,
                   blank_pref_election_ballot_data,
                   election_group_generator,
                   logged_in_user):
    """Allow and deny scenarios for vote."""
    election_group = election_group_generator(
        owner=is_owner,
        logged_in_user_in_census=as_logged_in_user,
        running=True
    )
    pollbook = election_group.elections[0].pollbooks[0]
    logged_in_feide_id = next(x.id_value for x in
                              logged_in_user.person.identifiers if
                              x.id_type == 'feide_id')
    if as_logged_in_user:
        voter = next(x for x in pollbook.voters if
                     x.id_value == logged_in_feide_id)
    else:
        voter = pollbook.voters[0]
    variables = {
        'voterId': str(voter.id),
        'ballot': json.dumps(blank_pref_election_ballot_data(pollbook))
    }
    mutation = """
    mutation ($voterId: UUID!, $ballot: JSONString!) {
        vote(voterId: $voterId, ballot: $ballot) {
            ballotId
            ok
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['vote']
    assert response['ok'] == is_allowed


@reg.add_scenario('addElectionGroupKeyBackup', 'allow')
@reg.add_scenario('addElectionGroupKeyBackup', 'deny')
@pytest.mark.parametrize("is_owner,is_allowed", [(True, True), (False, False)])
def test_auth_add_election_group_key_backup(db_session,
                                            is_owner,
                                            is_allowed,
                                            client,
                                            election_group_generator,
                                            master_key):
    """Allow and deny scenarios for addElectionGroupKeyBackup."""
    election_group = election_group_generator(owner=is_owner)
    _, master_key = master_key(db_session)
    variables = {
        'electionGroupId': str(election_group.id),
        'encryptedPrivKey': 'Test123',
        'masterKeyId': str(master_key.id)
    }
    mutation = """
    mutation (
        $electionGroupId: UUID!
        $encryptedPrivKey: String!
        $masterKeyId: UUID!
    ) {
        addElectionGroupKeyBackup(
            electionGroupId: $electionGroupId
            encryptedPrivKey: $encryptedPrivKey
            masterKeyId: $masterKeyId
        ) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation, variables=variables, context=get_test_context(db_session))
    response = execution['data']['addElectionGroupKeyBackup']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@pytest.mark.parametrize(
    'mutation,scenario',
    list(itertools.product(
        list(schema.get_mutation_type().fields.keys()), ['allow', 'deny'])))
def test_mutation_test_coverage(mutation, scenario):
    """Ensure required tests mutation authorization."""
    assert reg.operations_test_exist_for_scenario(mutation, scenario), (
        "Missing test scenario {} for mutation {}".format(scenario, mutation))
