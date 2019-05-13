import pytest

from evalg.authorization import (allows,
                                 PermissionDenied)
from evalg.authorization import permissions
from evalg.database.query import get_or_create
from evalg.models.authorization import (ElectionGroupRole,
                                        PersonPrincipal)


def test_requirements_throw_PermissionDenied_on_deny(
        db_session, logged_in_user, group_foo):
    with pytest.raises(PermissionDenied):
        allows.run([
            permissions.IsElectionGroupAdmin(election_group_id=group_foo.id)
        ])


def test_can_manage_election_group_denies(db_session, logged_in_user, election_group_foo):
    assert not permissions.can_manage_election_group(
        user=logged_in_user,
        election_group_id=election_group_foo.id)


def test_can_manage_election_group_allows(db_session, logged_in_user, election_group_foo):
    principal = get_or_create(
        db_session,
        PersonPrincipal,
        person_id=logged_in_user.person.id)
    db_session.add(principal)
    db_session.flush()
    role = get_or_create(
        db_session,
        ElectionGroupRole,
        name='admin',
        group_id=election_group_foo.id,
        principal_id=principal.id)
    db_session.add(role)
    db_session.flush()
    assert permissions.can_manage_election_group(
        user=logged_in_user,
        election_group_id=election_group_foo.id)
