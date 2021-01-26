import uuid

import evalg.database.query
import evalg.proc.authz
from evalg.graphql import get_context
from evalg.models.authorization import PersonIdentifierPrincipal
from evalg.models.person import PersonIdType


add_election_group_role_by_identifier_mutation = """
    mutation addElectionGroupRoleByIdentifier($electionGroupId: UUID!, $role: ElectionGroupRoleType!, $idType: PersonIdType!, $idValue: String!) {
        addElectionGroupRoleByIdentifier(electionGroupId: $electionGroupId, role: $role, idType: $idType, idValue: $idValue) {
            success
            code
            message
        }
    }
"""


def test_add_election_admin_by_identifier_validates_id_type(
        db_session,
        election_group_generator,
        client):
    """
    Ensure addElectionGroupRoleByIdentifier validates the idType field.
    """
    election_group = election_group_generator(owner=True)
    variables = {
        'electionGroupId': str(election_group.id),
        'role': 'admin',
        'idType': 'bogus',
        'idValue': 'random@example.org',
    }
    execution = client.execute(
        add_election_group_role_by_identifier_mutation,
        variables=variables,
        context=get_context())
    error_message = 'Expected type "PersonIdType", found "bogus"'
    assert any([error_message in x.get('message', '')
                for x in execution['errors']])


def test_add_election_admin_by_identifier_validates_role_type(
        db_session,
        election_group_generator,
        client):
    """
    Ensure addElectionGroupRoleByIdentifier validates the role field.
    """
    election_group = election_group_generator(owner=True)
    variables = {
        'electionGroupId': str(election_group.id),
        'role': 'bogus',
        'idType': 'feide_id',
        'idValue': 'random@example.org',
    }
    execution = client.execute(
        add_election_group_role_by_identifier_mutation,
        variables=variables,
        context=get_context())
    error_message = 'Expected type "ElectionGroupRoleType", found "bogus"'
    assert any([error_message in x.get('message', '')
                for x in execution['errors']])


def test_add_election_admin_when_election_group_does_not_exist(
        db_session,
        logged_in_user,
        client):
    """
    Ensure addElectionGroupRoleByIdentifier fails gracefully when the election
    group does not exist.
    """
    variables = {
        'electionGroupId': str(uuid.uuid4()),
        'role': 'admin',
        'idType': PersonIdType('feide_id').value,
        'idValue': 'random@example.org',
    }
    execution = client.execute(
        add_election_group_role_by_identifier_mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addElectionGroupRoleByIdentifier']
    assert response['success'] is False
    assert response['code'] == 'election-group-not-found'


def test_add_election_admin_by_identifier_denies(
        db_session,
        election_group_generator,
        client):
    """
    Ensure addElectionGroupRoleByIdentifier disallows adding new roles if the
    current user is not an admin for the election.
    """
    election_group = election_group_generator()
    variables = {
        'electionGroupId': str(election_group.id),
        'role': 'admin',
        'idType': PersonIdType('feide_id').value,
        'idValue': 'someonerandom@example.org',
    }
    execution = client.execute(
        add_election_group_role_by_identifier_mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addElectionGroupRoleByIdentifier']
    assert response['success'] is False
    assert response['code'] == 'permission-denied'


def test_add_election_admin_by_identifier(
        db_session,
        election_group_generator,
        logged_in_user,
        client):
    """
    Ensure the addElectionGroupRoleByIdentifier mutation allows adding new admins
    if the current user is an admin for the election.
    """
    election_group = election_group_generator(owner=True)
    variables = {
        'electionGroupId': str(election_group.id),
        'role': 'admin',
        'idType': PersonIdType('feide_id').value,
        'idValue': 'random@example.org',
    }
    # Give the logged in user a role
    principal = evalg.proc.authz.get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=logged_in_user.person.id,
    )
    evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=election_group,
        principal=principal,
        role_name='admin',
    )
    execution = client.execute(
        add_election_group_role_by_identifier_mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['addElectionGroupRoleByIdentifier']
    assert response['success'] is True
    assert response['code'] == 'role-added'
    # Make sure the created principal exists
    created_principal = evalg.database.query.lookup(
        db_session,
        PersonIdentifierPrincipal,
        id_type='feide_id',
        id_value='random@example.org')
    assert any([x.group == election_group
                and x.name == 'admin'
                for x in created_principal.roles])


remove_election_group_role_by_grant_mutation = """
    mutation removeElectionGroupRoleByGrant($grantId: UUID!) {
        removeElectionGroupRoleByGrant(grantId: $grantId) {
            success
            code
            message
        }
    }
"""


def test_remove_election_group_role_by_grant(
        db_session,
        election_group_generator,
        logged_in_user,
        client):
    """
    Ensure removeElectionGroupRoleByGrant removes the specified role grant.
    """
    election_group = election_group_generator(owner=True)
    # Give the logged in user a role
    admin_principal = evalg.proc.authz.get_or_create_principal(
        session=db_session,
        principal_type='person',
        person_id=logged_in_user.person.id,
    )
    evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=election_group,
        principal=admin_principal,
        role_name='admin',
    )
    # Create a role to be removed
    principal = evalg.proc.authz.get_or_create_principal(
        session=db_session,
        principal_type='person_identifier',
        id_type='feide_id',
        id_value='random@example.org',
    )
    role_to_be_removed = evalg.proc.authz.add_election_group_role(
        session=db_session,
        election_group=election_group,
        principal=principal,
        role_name='admin')
    grant_id = str(role_to_be_removed.grant_id)
    variables = {
        'grantId': grant_id,
    }
    execution = client.execute(
        remove_election_group_role_by_grant_mutation,
        variables=variables,
        context=get_context())
    assert not execution.get('errors')
    response = execution['data']['removeElectionGroupRoleByGrant']
    assert response['success'] is True
    assert response['code'] == 'role-removed'
    assert evalg.proc.authz.get_role_by_grant_id(db_session, grant_id) is None
