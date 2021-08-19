"""Mutations for the evalg GraphQL API."""
import graphene

from . import nodes


class ElectionMutations(graphene.ObjectType):
    """Mutations container class"""
    # ElectionGroup
    create_new_election_group = \
        nodes.election_group.CreateNewElectionGroup.Field()
    update_base_settings = \
        nodes.election_group.UpdateBaseSettings.Field()
    publish_election_group = \
        nodes.election_group.PublishElectionGroup.Field()
    unpublish_election_group = \
        nodes.election_group.UnpublishElectionGroup.Field()
    set_election_group_key = \
        nodes.election_group.SetElectionGroupKey.Field()
    start_election_group_count = \
        nodes.election_group.CountElectionGroup.Field()
    update_election_group_name = \
        nodes.election_group.UpdateElectionGroupName.Field()

    # Election
    update_voting_periods = \
        nodes.election.UpdateVotingPeriods.Field()
    update_voter_info = \
        nodes.election.UpdateVoterInfo.Field()

    # ElectionList
    add_election_list = \
        nodes.candidates.AddElectionList.Field()
    update_election_list = \
        nodes.candidates.UpdateElectionList.Field()
    delete_election_list = \
        nodes.candidates.DeleteElectionList.Field()

    # Candidates
    update_pref_elec_candidate = \
        nodes.candidates.UpdatePrefElecCandidate.Field()
    add_pref_elec_candidate = \
        nodes.candidates.AddPrefElecCandidate.Field()
    update_team_pref_elec_candidate = \
        nodes.candidates.UpdateTeamPrefElecCandidate.Field()
    add_team_pref_elec_candidate = \
        nodes.candidates.AddTeamPrefElecCandidate.Field()
    update_list_elec_candidate = \
        nodes.candidates.UpdateListElecCandidate.Field()
    add_list_elec_candidate = \
        nodes.candidates.AddListElecCandidate.Field()
    delete_candidate = \
        nodes.candidates.DeleteCandidate.Field()

    # Pollbook
    add_voter_by_person_id = \
        nodes.pollbook.AddVoterByPersonId.Field()
    add_voter_by_identifier = \
        nodes.pollbook.AddVoterByIdentifier.Field()
    update_voter_pollbook = \
        nodes.pollbook.UpdateVoterPollbook.Field()
    update_voter_reason = \
        nodes.pollbook.UpdateVoterReason.Field()
    delete_voter = \
        nodes.pollbook.DeleteVoter.Field()
    delete_voters_in_pollbook = \
        nodes.pollbook.DeleteVotersInPollbook.Field()
    upload_census_file = \
        nodes.pollbook.UploadCensusFile.Field()
    review_voter = \
        nodes.pollbook.ReviewVoter.Field()
    undo_review_voter = \
        nodes.pollbook.UndoReviewVoter.Field()

    # Roles
    add_election_group_role_by_identifier = \
        nodes.roles.AddElectionGroupRoleByIdentifier.Field()
    remove_election_group_role_by_grant = \
        nodes.roles.RemoveElectionGroupRoleByGrant.Field()

    # Votes
    vote = nodes.votes.AddVote.Field()

    # ElectionGroupKeysBackups
    add_election_group_key_backup = (
        nodes.privkeys_backup.AddElectionGroupKeyBackup.Field())
