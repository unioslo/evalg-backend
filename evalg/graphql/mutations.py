"""
Mutations for the evalg GraphQL API.
"""
import graphene

from . import nodes


class ElectionMutations(graphene.ObjectType):

    # ElectionGroup
    create_new_election_group = \
        nodes.election_group.CreateNewElectionGroup.Field()
    update_base_settings = \
        nodes.election_group.UpdateBaseSettings.Field()
    publish_election_group = \
        nodes.election_group.PublishElectionGroup.Field()
    unpublish_election_group = \
        nodes.election_group.UnpublishElectionGroup.Field()
    announce_election_group = \
        nodes.election_group.AnnounceElectionGroup.Field()
    unannounce_election_group = \
        nodes.election_group.UnannounceElectionGroup.Field()
    set_election_group_key = \
        nodes.election_group.SetElectionGroupKey.Field()
    start_election_group_count = \
        nodes.election_group.CountElectionGroup.Field()

    # Election
    update_voting_periods = \
        nodes.election.UpdateVotingPeriods.Field()
    update_voter_info = \
        nodes.election.UpdateVoterInfo.Field()

    # Candidates
    update_pref_elec_candidate = \
        nodes.candidates.UpdatePrefElecCandidate.Field()
    add_pref_elec_candidate = \
        nodes.candidates.AddPrefElecCandidate.Field()
    update_team_pref_elec_candidate = \
        nodes.candidates.UpdateTeamPrefElecCandidate.Field()
    add_team_pref_elec_candidate = \
        nodes.candidates.AddTeamPrefElecCandidate.Field()
    delete_candidate = \
        nodes.candidates.DeleteCandidate.Field()

    # PollBook
    add_voter = \
        nodes.pollbook.AddVoterByPersonId.Field()
    add_voter_by_id = \
        nodes.pollbook.AddVoterByIdentifier.Field()
    update_voter_pollbook = \
        nodes.pollbook.UpdateVoterPollBook.Field()
    update_voter_reason = \
        nodes.pollbook.UpdateVoterReason.Field()
    delete_voter = \
        nodes.pollbook.DeleteVoter.Field()
    delete_voters_in_pollbook = \
        nodes.pollbook.DeleteVotersInPollBook.Field()
    upload_census_file = \
        nodes.pollbook.UploadCensusFile.Field()
    review_self_added_voter = \
        nodes.pollbook.ReviewSelfAddedVoter.Field()
    undo_review_self_added_voter = \
        nodes.pollbook.UndoReviewSelfAddedVoter.Field()

    # Roles
    add_election_group_role_by_identifier = \
        nodes.roles.AddElectionGroupRoleByIdentifier.Field()
    remove_election_group_role_by_grant = \
        nodes.roles.RemoveElectionGroupRoleByGrant.Field()

    # Votes
    vote = nodes.votes.AddVote.Field()
