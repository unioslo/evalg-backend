"""Test authorization for mutations."""

import datetime
import itertools
import random
import string

import pytest

from evalg.graphql import schema, get_context
from evalg.models.election import ElectionGroup

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
        election_generator,
        make_full_election):
    """Allowed and denied scenario tests of publishing and announcing."""

    #election_objects = make_full_election('test publishing auth')
    #election_group = election_objects['election_group']

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
@pytest.mark.parametrize("is_admin", [True, False])
def test_auth_set_election_group_key(is_admin,
                                     client,
                                     election_keys_foo,
                                     logged_in_user,
                                     election_generator):

    election_group = election_generator(
        'test_auth_key',
        owner=logged_in_user if is_admin else None,
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
    assert response['success'] == is_admin
    if not is_admin:
        assert response['code'] == 'permission-denied'
    election_group_db = ElectionGroup.query.get(election_group.id)
    assert ((election_group_db.public_key == election_keys_foo['public']) ==
            is_admin), "Different key in db then expected."


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

@pytest.mark.xfail
@pytest.mark.parametrize(
    'mutation,scenario,',
    list(itertools.product(
        list(schema.get_mutation_type().fields.keys()),
        ['allow', 'deny'])))
def test_mutation_test_coverage(mutation, scenario):
    """Ensure required test mutation."""
    assert reg.operations_test_exist_for_scenario(mutation, scenario), (
        "Missing test scenario {} for mutation {}".format(scenario,
                                                          mutation))
