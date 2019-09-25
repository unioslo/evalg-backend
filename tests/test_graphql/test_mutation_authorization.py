"""Test authorization for mutations."""

import datetime
import io
import itertools
import json
import random
import string

import nacl.encoding
import nacl.public
import pytest
from werkzeug.test import EnvironBuilder

from evalg.graphql import schema, get_context
from evalg.models.ballot import Envelope
from evalg.models.candidate import Candidate
from evalg.models.election import ElectionGroup
from evalg.models.election_list import ElectionList
from evalg.models.pollbook import Pollbook
from evalg.models.voter import Voter
from evalg.proc.pollbook import ElectionVoterPolicy

from .utils.register import RegisterOperationTestScenario


reg = RegisterOperationTestScenario()


@reg.add_scenario('createNewElectionGroup', 'allow')
@reg.add_scenario('createNewElectionGroup', 'deny')
def test_allow_create_new_election_group(make_ou, client, logged_in_user):
    """
    Allow and deny scenario of createNewElectionGroup.

    This mutations is always allowed so no need to test denying.
    """
    template_name = 'uio_dean'
    name_rand = ''.join(random.choices(string.ascii_lowercase, k=10))
    ou_name = 'ou-{}'.format(name_rand)
    ou = make_ou(ou_name)
    variables = {
        'ouId': str(ou.id),
        'template': True,
        'templateName': template_name
    }
    mutation = """
    mutation ($ouId: UUID!, $template: Boolean!, $templateName: String!) {
        createNewElectionGroup(ouId: $ouId,
                               template: $template,
                               templateName: $templateName) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['createNewElectionGroup']
    assert response['ok']


# @reg.add_scenario('updateBaseSettings', 'allow')
def test_allow_update_base_settings():
    pass


publishing_mutations = {
    "publishElectionGroup": """
    mutation ($id: UUID!) {
        publishElectionGroup(id: $id) {
            success
            code
        }
    }""",
    "unpublishElectionGroup": """
    mutation ($id: UUID!) {
        unpublishElectionGroup(id: $id) {
            success
            code
        }
    }""",
    "announceElectionGroup": """
    mutation ($id: UUID!) {
        announceElectionGroup(id: $id) {
            success
            code
        }
    }""",
    "unannounceElectionGroup": """
    mutation ($id: UUID!) {
        unannounceElectionGroup(id: $id) {
            success
            code
        }
    }""",
}

publishing_testdata = [
    ('publishElectionGroup',
     True,
     {'published': False, 'announced': False},
     {'published': True, 'announced': False}),
    ('publishElectionGroup',
     False,
     {'published': False, 'announced': False},
     {'published': False, 'announced': False}),
    ('unpublishElectionGroup',
     True,
     {'published': True, 'announced': False},
     {'published': False, 'announced': False}),
    ('unpublishElectionGroup',
     False,
     {'published': True, 'announced': False},
     {'published': True, 'announced': False}),
    ('announceElectionGroup',
     True,
     {'published': False, 'announced': False},
     {'published': False, 'announced': True}),
    ('announceElectionGroup',
     False,
     {'published': False, 'announced': False},
     {'published': False, 'announced': False}),
    ('unannounceElectionGroup',
     True,
     {'published': False, 'announced': True},
     {'published': False, 'announced': False}),
    ('unannounceElectionGroup',
     False,
     {'published': False, 'announced': True},
     {'published': False, 'announced': True}),
]


@reg.add_scenario('publishElectionGroup', 'allow')
@reg.add_scenario('publishElectionGroup', 'deny')
@reg.add_scenario('unpublishElectionGroup', 'allow')
@reg.add_scenario('unpublishElectionGroup', 'deny')
@reg.add_scenario('announceElectionGroup', 'allow')
@reg.add_scenario('announceElectionGroup', 'deny')
@reg.add_scenario('unannounceElectionGroup', 'allow')
@reg.add_scenario('unannounceElectionGroup', 'deny')
@pytest.mark.parametrize(
    "mutation_name,is_publisher,init_status,expected_result",
    publishing_testdata
)
def test_auth_publish_and_announce_election_group(
        mutation_name,
        is_publisher,
        init_status,
        expected_result,
        db_session,
        client,
        logged_in_user,
        make_person_publisher,
        election_generator):
    """Allowed and denied scenario tests of publishing and announcing."""

    election_group = election_generator(
        'test publishing auth',
        owner=logged_in_user,
        with_key=True
    )

    if init_status['published']:
        election_group.publish()
    else:
        election_group.unpublish()
    if init_status['announced']:
        election_group.announce()
    else:
        election_group.unannounce()
    db_session.flush()

    if is_publisher:
        make_person_publisher(logged_in_user.person)

    mutation = publishing_mutations[mutation_name]
    variables = {'id': str(election_group.id)}
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors'), "Mutation return error"
    result = execution['data'][mutation_name]
    assert result['success'] == is_publisher, (
        "The mutation did not return the expected success value")

    if not is_publisher:
        assert result['code'] == 'permission-denied'

    eg_after = ElectionGroup.query.get(election_group.id)
    assert (eg_after.published == expected_result['published'] and
            eg_after.announced == expected_result['announced']), (
        "Election group in db does not match expected state")


@reg.add_scenario('setElectionGroupKey', 'allow')
@reg.add_scenario('setElectionGroupKey', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_set_election_group_key(is_admin,
                                     is_allowed,
                                     client,
                                     election_keys_foo,
                                     logged_in_user,
                                     election_generator):

    election_group = election_generator(
        'test_auth_key',
        owner=logged_in_user if is_admin else None,
        with_key=False,
    )
    variables = {
        'id': str(election_group.id),
        'publicKey': election_keys_foo['public']
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
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['setElectionGroupKey']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'
    election_group_db = ElectionGroup.query.get(election_group.id)
    assert ((election_group_db.public_key == election_keys_foo['public']) ==
            is_allowed), "Different key in db then expected."


@pytest.mark.xfail
@pytest.mark.parametrize('is_admin', [True, False])
def test_auth_start_election_group_count(is_admin,
                                         client,
                                         election_keys_foo,
                                         make_election_group,
                                         logged_in_user):
    """TODO user make_full_election not eleciton_group_bar"""

    election_group = make_election_group(
        'test auth start election count',
        announced_at=(datetime.datetime.now(datetime.timezone.utc) -
                      datetime.timedelta(days=3)),
        published_at=(datetime.datetime.now(datetime.timezone.utc) -
                      datetime.timedelta(days=3)),
        admin=True
    )

    variables = {
        'id': str(election_group.id),
        'electionKey': election_keys_foo['private']
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
        mutation,
        variables=variables,
        context=get_context())

    assert not execution.get('errors')
    response = execution['data']['startElectionGroupCount']
    assert response['success'] == is_admin
    if not is_admin:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('updatePrefElecCandidate', 'allow')
@reg.add_scenario('updatePrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_update_pref_elec_candidate(is_admin,
                                         is_allowed,
                                         client,
                                         election_generator,
                                         logged_in_user):
    """Allowed and denied scenario tests of updatePrefElecCandidate."""
    election_group = election_generator(
        'test_auth_delete_candidate',
        template_name='uio_university_board',
        owner=logged_in_user if is_admin else None,
        with_candidates=True,
    )
    election_list = election_group.elections[0].lists[0]
    candidate = election_group.elections[0].lists[0].candidates[0]
    new_name = '{} Testesen'.format(candidate.name)
    variables = {
        'gender': candidate.meta['gender'],
        'listId': str(election_list.id),
        'id': str(candidate.id),
        'name': new_name,
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
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['updatePrefElecCandidate']
    assert response['ok'] == is_allowed
    candidate_db = Candidate.query.get(candidate.id)

    assert (candidate_db.name == new_name) == is_allowed, (
        "Candidate should not have been updated")


@reg.add_scenario('addPrefElecCandidate', 'allow')
@reg.add_scenario('addPrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_add_pref_elec_candidate(is_admin,
                                      is_allowed,
                                      client,
                                      election_generator,
                                      logged_in_user):
    """Allowed and denied scenario tests of addPrefElecCandidate."""
    election_group = election_generator(
        'test_auth_delete_candidate',
        template_name='uio_university_board',
        owner=logged_in_user if is_admin else None,
        with_candidates=False,
    )
    election_list = election_group.elections[0].lists[0]
    variables = {
        'gender': 'female',
        'listId': str(election_list.id),
        'name': 'Test Testesen',
    }
    mutation = """
    mutation ($gender: String!, $listId: UUID!, $name: String!) {
        addPrefElecCandidate(gender: $gender, listId: $listId , name: $name) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addPrefElecCandidate']
    assert response['ok'] == is_allowed
    election_list_db = ElectionList.query.get(election_list.id)
    assert ((len(election_list_db.candidates) != 0) == is_allowed), (
        "Candidate should not have been added")


@reg.add_scenario('updateTeamPrefElecCandidate', 'allow')
@reg.add_scenario('updateTeamPrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_update_team_pref_elec_candidate(is_admin,
                                              is_allowed,
                                              client,
                                              election_generator,
                                              logged_in_user):
    """Allowed and denied scenario tests of updatePrefElecCandidate."""
    election_group = election_generator(
        'test_auth_delete_candidate',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
        with_candidates=True,
    )
    election_list = election_group.elections[0].lists[0]
    candidate = election_group.elections[0].lists[0].candidates[0]
    new_name = '{} Testesen'.format(candidate.name)
    variables = {
        'coCandidates': candidate.meta['co_candidates'],
        'listId': str(election_list.id),
        'id': str(candidate.id),
        'name': new_name,
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
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['updateTeamPrefElecCandidate']
    assert response['ok'] == is_allowed
    candidate_db = Candidate.query.get(candidate.id)

    assert (candidate_db.name == new_name) == is_allowed, (
        "Candidate should not have been updated")


@reg.add_scenario('addTeamPrefElecCandidate', 'allow')
@reg.add_scenario('addTeamPrefElecCandidate', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_add_team_pref_elec_candidate(is_admin,
                                           is_allowed,
                                           client,
                                           election_generator,
                                           logged_in_user):
    """Allowed and denied scenario tests of addTeamPrefElecCandidate."""
    election_group = election_generator(
        'test_auth_delete_team_candidate',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
        with_candidates=False,
    )
    election_list = election_group.elections[0].lists[0]
    variables = {
        'coCandidates': [{'name': 'Test Testemeresen'}],
        'listId': str(election_list.id),
        'name': 'Test Testesen',
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
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addTeamPrefElecCandidate']
    assert response['ok'] == is_allowed
    election_list_db = ElectionList.query.get(election_list.id)
    assert ((len(election_list_db.candidates) != 0) == is_allowed), (
        "Candidate should not have been added")


@reg.add_scenario('deleteCandidate', 'allow')
@reg.add_scenario('deleteCandidate', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_delete_candidate(is_admin,
                               is_allowed,
                               client,
                               election_generator,
                               logged_in_user):

    election_group = election_generator(
        'test_auth_delete_candidate',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )

    candidate = election_group.elections[0].candidates[0]

    variables = {
        'id': str(candidate.id),
    }

    mutation = """
    mutation ($id: UUID!) {
        deleteCandidate(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['deleteCandidate']
    assert response['ok'] == is_allowed
    candidate_db = Candidate.query.get(candidate.id)
    assert (not candidate_db) == is_allowed, (
        'Candidate deleted status not as expected')


@reg.add_scenario('addVoterByPersonId', 'allow')
@reg.add_scenario('addVoterByPersonId', 'deny')
@pytest.mark.parametrize(
    "is_admin,as_current_user,is_allowed",
    [
        # Admins can add themselves to pollbooks
        (True, True, True),
        # Admins can add others to pollbook
        (True, False, True),
        # Users can add themselves to pollbooks
        (False, True, True),
        # Users are not allowed to add others to a pollbook
        (False, False, False)])
def test_auth_add_voter_by_person_id(is_admin,
                                     as_current_user,
                                     is_allowed,
                                     client,
                                     election_generator,
                                     person_generator,
                                     logged_in_user):

    election_group = election_generator(
        'test_auth_add_voter_by_id',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    pollbook = election_group.elections[0].pollbooks[0]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    variables = {
        'personId': str(person.id),
        'pollbookId': str(pollbook.id),
    }
    mutation = """
    mutation ($personId: UUID!, $pollbookId: UUID!) {
        addVoterByPersonId(personId: $personId, pollbookId: $pollbookId) {
            id
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addVoterByPersonId']
    assert (response is not None) == is_allowed
    pollbook_db = Pollbook.query.get(pollbook.id)
    assert len(pollbook_db.voters) == (1 if is_allowed else 0)


@reg.add_scenario('addVoterByIdentifier', 'allow')
@reg.add_scenario('addVoterByIdentifier', 'deny')
@pytest.mark.parametrize(
    "is_admin,as_current_user,is_allowed",
    [
        # Admins can add themselves to pollbooks
        (True, True, True),
        # Admins can add others to pollbook
        (True, False, True),
        # Users are not allowed to add themselves to pollbooks
        (False, True, False),
        # Users are not allowed to add others to a pollbook
        (False, False, False)])
def test_auth_add_voter_by_identifier(is_admin,
                                     as_current_user,
                                     is_allowed,
                                     client,
                                     election_generator,
                                     person_generator,
                                     logged_in_user):

    election_group = election_generator(
        'test_auth_add_voter_by_identifier',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    pollbook = election_group.elections[0].pollbooks[0]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    feide_id = next(i for i in person.identifiers if i.id_type == 'feide_id')
    variables = {
        'idType': feide_id.id_type,
        'idValue': feide_id.id_value,
        'pollbookId': str(pollbook.id),
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
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addVoterByIdentifier']
    assert (response is not None) == is_allowed
    pollbook_db = Pollbook.query.get(pollbook.id)
    assert len(pollbook_db.voters) == (1 if is_allowed else 0)


@reg.add_scenario('updateVoterPollbook', 'allow')
@reg.add_scenario('updateVoterPollbook', 'deny')
@pytest.mark.parametrize(
    "is_admin,as_current_user,same_election_group,same_owner,is_allowed",
    [
        # Admins can move themselves
        (True, True, True, True, True),
        # Admins can move others
        (True, False, True, True, True),
        # Users are not allowed to move themselves
        (False, True, True, True, False),
        # Users are not allowed to move others
        (False, False, True, True, False),
        # Admins can't move themselves between to election_groups they own
        (True, True, False, True, False),
        # Admins can't move others between to election_groups they own
        (True, False, False, True, False),
        # Users can't move themselves between to election_groups
        (False, True, False, True, False),
        # Users can't move others between to election_groups
        (False, False, False, True, False),
        # Admins can't move themselves to election_groups not owned by them
        (True, True, False, False, False),
        # Admins can't move user to election_groups not owned by them
        (True, False, False, False, False),
    ])
def test_auth_update_voter_pollbook(db_session,
                                    is_admin,
                                    as_current_user,
                                    same_election_group,
                                    same_owner,
                                    is_allowed,
                                    client,
                                    election_generator,
                                    person_generator,
                                    logged_in_user):

    election_group_1 = election_generator(
        'test_auth_add_voter_by_identifier',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    pollbook_1 = election_group_1.elections[0].pollbooks[0]

    if not same_election_group:
        election_group_2 = election_generator(
            'test_auth_add_voter_by_identifier_2',
            template_name='uio_principal',
            owner=logged_in_user if (is_admin and same_owner) else None,
        )
        pollbook_2 = election_group_2.elections[0].pollbooks[0]
    else:
        pollbook_2 = election_group_1.elections[0].pollbooks[1]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook_1, person)
    db_session.commit()
    variables = {
        'id': str(voter.id),
        'pollbookId': str(pollbook_2.id),
    }
    mutation = """
    mutation ($id: UUID!, $pollbookId: UUID!) {
        updateVoterPollbook(id: $id, pollbookId: $pollbookId) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['updateVoterPollbook']
    assert response['ok'] == is_allowed
    assert (len(pollbook_1.voters) == 0) == is_allowed
    assert (len(pollbook_2.voters) == 1) == is_allowed


@reg.add_scenario('updateVoterReason', 'allow')
@reg.add_scenario('updateVoterReason', 'deny')
@pytest.mark.parametrize(
    "is_admin,as_current_user,is_allowed",
    [(True, True, True),
     (False, True, True),
     # Admins should not be able to update reason in elections
     (True, False, False),
     # Users should not be able to update reason for other users
     (False, False, False)])
def test_update_voter_reason(db_session,
                             is_admin,
                             as_current_user,
                             is_allowed,
                             client,
                             election_generator,
                             person_generator,
                             logged_in_user):
    """Allow and deny scenarios for updateVoterReason."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )

    pollbook = election_group.elections[0].pollbooks[0]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    reason = 'Test 123'
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, reason=reason)
    db_session.commit()
    new_reason = 'Test mer 123 test setsetest'
    variables = {
        'id': str(voter.id),
        'reason': new_reason,
    }
    mutation = """
    mutation ($id: UUID!, $reason: String!) {
        updateVoterReason(id: $id, reason: $reason) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['updateVoterReason']
    assert response['ok'] == is_allowed

    voter_db = Voter.query.get(voter.id)

    if is_allowed:
        assert voter_db.reason == new_reason, (
            'Voter reason did not change')
    else:
        assert voter_db.reason == reason, (
            'Voter reason should not change')


delete_voter_test_input = [
    (True, True, False, False, True),
    (True, False, False, False, True),
    (False, True, False, False, False),
    (False, False, False, False, False),
    # Never allowed removal of self added voters or voters with votes
    (True, True, True, False, False),
    (True, False, True, False, False),
    (False, True, True, False, False),
    (False, False, True, False, False),
    (True, True, False, True, False),
    (True, False, False, True, False),
    (False, True, False, True, False),
    (False, False, False, True, False),
    (True, True, True, True, False),
    (True, False, True, True, False),
    (False, True, True, True, False),
    (False, False, True, True, False),
]


@reg.add_scenario('deleteVoter', 'allow')
@reg.add_scenario('deleteVoter', 'deny')
@pytest.mark.parametrize(
    "is_admin,as_current_user,self_added_voter,with_vote,is_allowed",
    delete_voter_test_input)
def test_auth_delete_voter(db_session,
                           is_admin,
                           as_current_user,
                           self_added_voter,
                           with_vote,
                           is_allowed,
                           client,
                           election_generator,
                           person_generator,
                           vote_generator,
                           logged_in_user):
    """Allow and deny scenarios for deleteVoter."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_faculty_board',
        owner=logged_in_user if is_admin else None,
    )
    pollbook = election_group.elections[0].pollbooks[0]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook,
                                   person,
                                   self_added=self_added_voter)

    if with_vote:
        vote = vote_generator(pollbook.election, voter)
        assert vote

    db_session.commit()
    variables = {
        'id': str(voter.id),
    }
    mutation = """
    mutation ($id: UUID!) {
        deleteVoter(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['deleteVoter']
    assert response['ok'] == is_allowed
    voter_db = Voter.query.get(voter.id)
    assert (voter_db is None) == is_allowed


delete_voters_in_pollbook_test_input = [
    (True, False, False, True),
    (True, False, True, True),
    (True, True, False, True),
    (True, True, True, True),
    (False, False, False, False),
    (False, False, True, False),
    (False, True, False, False),
    (False, True, True, False),
]


@reg.add_scenario('deleteVotersInPollbook', 'allow')
@reg.add_scenario('deleteVotersInPollbook', 'deny')
@pytest.mark.parametrize(
    "is_admin,with_self_added_voter,with_vote,is_allowed",
    delete_voters_in_pollbook_test_input)
def test_auth_delete_voters_in_pollbook(db_session,
                                        is_admin,
                                        with_self_added_voter,
                                        with_vote,
                                        is_allowed,
                                        client,
                                        election_generator,
                                        person_generator,
                                        vote_generator,
                                        logged_in_user):
    """Allow and deny scenarios for deleteVotersInPollbook."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_faculty_board',
        owner=logged_in_user if is_admin else None,
    )
    pollbook = election_group.elections[0].pollbooks[0]
    voter_policy = ElectionVoterPolicy(db_session)

    total_voters = 0
    expected_left = 0
    # Generate 4 admin added voters without votes
    person_admin_added = [person_generator() for _ in range(4)]

    voters_admin_added = [
        voter_policy.add_voter(pollbook, x, self_added=False) for x in
        person_admin_added]

    total_voters += len(voters_admin_added)

    if with_vote:
        voter = voter_policy.add_voter(pollbook, person_generator(),
                                       self_added=False)
        vote = vote_generator(pollbook.election, voter)
        assert vote
        total_voters += 1
        expected_left += 1

    if with_self_added_voter:
        voter_policy.add_voter(pollbook, person_generator(), self_added=True)
        total_voters += 1

    if with_vote and with_self_added_voter:
        voter = voter_policy.add_voter(pollbook, person_generator(),
                                       self_added=True)
        vote = vote_generator(pollbook.election, voter)
        assert vote
        total_voters += 1
        expected_left += 1

    db_session.commit()
    variables = {
        'id': str(pollbook.id),
    }
    mutation = """
    mutation ($id: UUID!) {
        deleteVotersInPollbook(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['deleteVotersInPollbook']
    assert response['ok'] == is_allowed

    if not is_allowed:
        expected_left = total_voters

    pollbook_db = Pollbook.query.get(pollbook.id)
    assert len(pollbook_db.voters) == expected_left


@reg.add_scenario('uploadCensusFile', 'allow')
@reg.add_scenario('uploadCensusFile', 'deny')
@pytest.mark.parametrize("is_admin,is_allowed", [(True, True), (False, False)])
def test_auth_upload_census_file(is_admin,
                                 is_allowed,
                                 client,
                                 logged_in_user,
                                 election_generator):
    """Allow and deny scenarios for uploadCensusFile."""
    election_group = election_generator(
        'test_upload_census_file',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    pollbook = election_group.elections[0].pollbooks[0]

    feide_ids = ['pederaas@uio.no', 'martekir@uio.no', 'larsh@uio.no',
                 'hansta@uio.no']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(feide_ids).encode('utf-8')),                                                                        
                 'usernames.txt')})

    variables = {
        'censusFile': builder.files['file'],
        'pollbookId': str(pollbook.id),
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
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['uploadCensusFile']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'
    else:
        assert response['numFailed'] == 0
        assert response['numOk'] == len(feide_ids)
    pollbook_db = Pollbook.query.get(pollbook.id)
    assert (len(pollbook_db.voters) == len(feide_ids)) == is_allowed


@reg.add_scenario('reviewVoter', 'allow')
@reg.add_scenario('reviewVoter', 'deny')
@pytest.mark.parametrize(
    'is_admin,as_current_user,verify,is_allowed',
    [(True, True, True, True),
     (True, True, False, True),
     (True, False, True, True),
     (True, False, False, True),
     (False, True, True, False),
     (False, True, False, False),
     (False, False, True, False),
     (False, False, False, False)])
def test_auth_review_voter(is_admin,
                           as_current_user,
                           verify,
                           is_allowed,
                           client,
                           db_session,
                           election_generator,
                           logged_in_user,
                           person_generator,

                           ):
    """Allow and deny scenarios for reviewVoter."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )

    pollbook = election_group.elections[0].pollbooks[0]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=True)
    db_session.commit()

    variables = {
        'id': str(voter.id),
        'verify': verify,
    }
    mutation = """
    mutation ($id: UUID!, $verify: Boolean!) {
        reviewVoter(id: $id, verify: $verify) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['reviewVoter']
    assert response['ok'] == is_allowed
    voter_db = Voter.query.get(voter.id)

    if is_allowed:
        assert voter_db.verified == verify
        assert voter_db.reviewed
    else:
        assert not voter_db.verified
        assert not voter_db.reviewed


@reg.add_scenario('undoReviewVoter', 'allow')
@reg.add_scenario('undoReviewVoter', 'deny')
@pytest.mark.parametrize(
    'is_admin,as_current_user,is_allowed',
    [(True, True, True),
     (True, False, True),
     (False, True, False),
     (False, False, False)])
def test_auth_undo_review_voter(is_admin,
                                as_current_user,
                                is_allowed,
                                client,
                                db_session,
                                election_generator,
                                logged_in_user,
                                person_generator):
    """Allow and deny scenarios for undoReviewVoter."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    pollbook = election_group.elections[0].pollbooks[0]
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook, person, self_added=True)
    voter.reviewed = True
    voter.verified = True
    db_session.add(voter)
    db_session.commit()

    variables = {
        'id': str(voter.id),
    }
    mutation = """
    mutation ($id: UUID!) {
        undoReviewVoter(id: $id) {
            ok
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['undoReviewVoter']
    assert response['ok'] == is_allowed
    voter_db = Voter.query.get(voter.id)

    if is_allowed:
        assert not voter_db.verified
        assert not voter_db.reviewed
    else:
        assert voter_db.verified
        assert voter_db.reviewed


@reg.add_scenario('addElectionGroupRoleByIdentifier', 'allow')
@reg.add_scenario('addElectionGroupRoleByIdentifier', 'deny')
@pytest.mark.parametrize(
    'is_admin,as_current_user,role,is_allowed',
    [(True, True, 'admin', True),
     (True, False, 'admin', True),
     (False, True, 'admin', False),
     (False, False, 'admin', False),
     (True, True, 'publisher', False),
     (True, False, 'publisher', False),
     (False, True, 'publisher', False),
     (False, False, 'publisher', False)])
def test_auth_add_election_group_role_by_identifier(is_admin,
                                                    as_current_user,
                                                    role,
                                                    is_allowed,
                                                    client,
                                                    election_generator,
                                                    logged_in_user,
                                                    person_generator):
    """Allow and deny scenarios for addElectionGroupRoleByIdentifier."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()

    feide_id = next(i for i in person.identifiers if i.id_type == 'feide_id')

    variables = {
        'electionGroupId': str(election_group.id),
        'idType': feide_id.id_type,
        'idValue': feide_id.id_value,
        'role': role,
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
        mutation,
        variables=variables,
        context=get_context())

    if role == 'admin':
        assert not execution.get('errors')
        response = execution['data']['addElectionGroupRoleByIdentifier']
        assert response['success'] == is_allowed
        if not is_allowed:
            assert response['code'] == 'permission-denied'
    else:
        # Admin is currently the only allowed role in the type.
        assert execution.get('errors')


@reg.add_scenario('removeElectionGroupRoleByGrant', 'allow')
@reg.add_scenario('removeElectionGroupRoleByGrant', 'deny')
@pytest.mark.xfail
@pytest.mark.parametrize(
    'is_admin,as_current_user,is_allowed',
    [(True, True, True),
     (True, False, True),
     # User is admin via the grant
     (False, True, True),
     (False, False, False)])
def test_auth_remove_election_group_role_by_grant(is_admin,
                                                  as_current_user,
                                                  is_allowed,
                                                  client,
                                                  election_generator,
                                                  grant_for_person_generator,
                                                  logged_in_user,
                                                  person_generator):
    """Allow and deny scenarios for addElectionGroupRoleByIdentifier."""

    # TODO try to remove grant
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
    )
    if as_current_user:
        person = logged_in_user.person
    else:
        person = person_generator()

    grant = grant_for_person_generator(person, election_group)

    variables = {
        'grantId': str(grant.grant_id),
    }
    mutation = """
    mutation ($grantId: UUID!) {
        removeElectionGroupRoleByGrant(grantId: $grantId) {
            success
            code
        }
    }
    """
    execution = client.execute(
        mutation,
        variables=variables,
        context=get_context())

    assert not execution.get('errors')
    response = execution['data']['removeElectionGroupRoleByGrant']
    assert response['success'] == is_allowed

    if not is_allowed:
        assert response['code'] == 'permission-denied'


@reg.add_scenario('vote', 'allow')
@reg.add_scenario('vote', 'deny')
@pytest.mark.parametrize(
    "is_admin,as_logged_in_user,is_allowed",
    [
        (True, True, True),
        (False, True, True),
        (True, False, False),
        (False, False, False),
    ]
)
def test_auth_vote(is_admin,
                   as_logged_in_user,
                   is_allowed,
                   client,
                   db_session,
                   ballot_data_generator,
                   election_generator,
                   logged_in_user,
                   person_generator):
    """Allow and deny scenarios for vote."""
    election_group = election_generator(
        'test_update_voter_reason',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,
        ready_for_voting=True,
    )
    pollbook = election_group.elections[0].pollbooks[0]
    if as_logged_in_user:
        person = logged_in_user.person
    else:
        person = person_generator()
    voter_policy = ElectionVoterPolicy(db_session)
    voter = voter_policy.add_voter(pollbook,
                                   person)
    variables = {
        'voterId': str(voter.id),
        'ballot': json.dumps(ballot_data_generator()),
    }
    mutation = """
    mutation ($voterId: UUID!, $ballot: JSONString!) {
        vote(voterId: $voterId, ballot: $ballot) {
            ballotId
            ok
        }
    }
    """
    execution = client.execute(mutation,
                               variables=variables,
                               context=get_context())
    assert not execution.get('errors')
    response = execution['data']['vote']
    assert response['ok'] == is_allowed

    if is_allowed:
        assert Envelope.query.get(response['ballotId'])


@reg.add_scenario('addElectionGroupKeyBackup', 'allow')
@reg.add_scenario('addElectionGroupKeyBackup', 'deny')
@pytest.mark.parametrize(
    "is_admin,is_allowed",
    [(True, True), (False, False)])
def test_auth_add_election_group_key_backup(is_admin,
                                            is_allowed,
                                            client,
                                            election_generator,
                                            logged_in_user,
                                            make_master_key):
    """Allow and deny scenarios for addElectionGroupKeyBackup."""
    privkey, master_key = make_master_key()

    election_group = election_generator(
        'test_add_election_group_key_backup',
        template_name='uio_dean',
        owner=logged_in_user if is_admin else None,

    )
    new_priv_key = nacl.public.PrivateKey.generate()
    message = new_priv_key.encode(encoder=nacl.encoding.Base64Encoder)
    ebox = nacl.public.Box(new_priv_key, privkey.public_key)
    encrypted_priv_key = ebox.encrypt(message,
                                      encoder=nacl.encoding.Base64Encoder)

    variables = {
        'electionGroupId': str(election_group.id),
        'encryptedPrivKey': encrypted_priv_key,
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
    # could put any str, but let's do things properly...
    execution = client.execute(mutation,
                               variables=variables,
                               context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addElectionGroupKeyBackup']
    assert response['success'] == is_allowed
    if not is_allowed:
        assert response['code'] == 'permission-denied'


@pytest.mark.xfail
@pytest.mark.parametrize(
    'mutation,scenario',
    list(itertools.product(
        list(schema.get_mutation_type().fields.keys()),
        ['allow', 'deny'])))
def test_mutation_test_coverage(mutation, scenario):
    """Ensure required tests mutation authorization."""
    assert reg.operations_test_exist_for_scenario(mutation, scenario), (
        "Missing test scenario {} for mutation {}".format(scenario,
                                                          mutation))
