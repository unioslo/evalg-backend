"""
The GraphQL ElectionGroup ObjectType.

This module defines the GraphQL ObjectType that represents MasterKey, as
well as queries and mutations for this object.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.election
import evalg.models.privkeys_backup

from evalg.graphql.nodes.utils.permissions import (
    can_manage_election_group,
    permission_controller,
    permission_controlled_default_resolver)
from evalg.graphql.nodes.utils.base import (get_session,
                                            get_current_user,
                                            MutationResponse)


@permission_controller.control_object_type
class MasterKey(graphene_sqlalchemy.SQLAlchemyObjectType):
    """Master-key"""

    class Meta:
        model = evalg.models.privkeys_backup.MasterKey
        default_resolver = permission_controlled_default_resolver


def resolve_master_keys(_, info):
    """List all election groups that should be visible to the current user."""
    return MasterKey.get_query(info).filter_by(active=True).all()


list_active_master_keys_query = graphene.List(
    MasterKey,
    resolver=resolve_master_keys)


class AddElectionGroupKeyBackupResponse(MutationResponse):
    """Mutation result class for the AddElectionGroupKeyBackup mutation."""
    pass


class AddElectionGroupKeyBackup(graphene.Mutation):
    """Adds a private key-backup for a given election-group"""

    class Arguments:

        election_group_id = graphene.UUID(required=True)
        master_key_id = graphene.UUID(required=True)
        encrypted_priv_key = graphene.String(required=True)

    Output = AddElectionGroupKeyBackupResponse

    def mutate(self, info, **args):
        """The mutation"""
        election_group_id = args['election_group_id']
        master_key_id = args['master_key_id']
        encrypted_priv_key = args['encrypted_priv_key']
        session = get_session(info)
        user = get_current_user(info)
        election_group = session.query(
            evalg.models.election.ElectionGroup).get(election_group_id)
        master_key = session.query(
            evalg.models.privkeys_backup.MasterKey).get(master_key_id)

        if not master_key:
            return AddElectionGroupKeyBackupResponse(
                success=False,
                code='master-key-not-found',
                message='Master key {} not found'.format(master_key_id))
        if not master_key.active:
            # don't just trust the frontend to filter properly
            return AddElectionGroupKeyBackupResponse(
                success=False,
                code='master-key-inactive',
                message='Master key {} is not active'.format(master_key_id))
        if not election_group:
            return AddElectionGroupKeyBackupResponse(
                success=False,
                code='election-group-not-found',
                message='Election group {} not found'.format(
                    election_group_id))
        if not user:
            return AddElectionGroupKeyBackupResponse(
                success=False,
                code='user-not-found',
                message='Could not find current user')
        if not can_manage_election_group(session, user, election_group):
            return AddElectionGroupKeyBackupResponse(
                success=False,
                code='permission-denied',
                message=('Not allowed to set election group key backup for '
                         'election group {}').format(election_group_id))
        egk_backup = evalg.models.privkeys_backup.ElectionGroupKeyBackup(
            encrypted_priv_key=encrypted_priv_key,
            election_group_id=election_group_id,
            master_key_id=master_key_id)
        # No apparent errors to be expected. Invalidate all previous backups!
        session.query(
            evalg.models.privkeys_backup.ElectionGroupKeyBackup).filter_by(
                election_group_id=election_group_id,
                master_key_id=master_key_id,
                active=True).update({'active': False},
                                    synchronize_session=False)
        session.commit()
        session.add(egk_backup)
        session.commit()
        return AddElectionGroupKeyBackupResponse(success=True)
