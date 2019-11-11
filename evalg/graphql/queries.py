"""
Queries for the evalg GraphQL API.
"""

import graphene

from . import nodes


class ElectionQuery(graphene.ObjectType):
    """Query container class"""
    # Elections and election groups
    election_groups = nodes.election_group.list_election_groups_query
    election_group = nodes.election_group.get_election_group_query
    election_group_key_meta = nodes.election_group.get_election_key_meta_query
    persons_with_multiple_verified_voters = \
        nodes.election_group.persons_with_multiple_verified_voters_query
    election_template = nodes.election_group.get_election_template_query

    # Election results
    election_group_count = \
        nodes.election_group.get_election_group_count_query
    # TODO: Why isn't this called ``election_group_counts`` in line with the
    #   convention.
    election_group_counting_results = \
        nodes.election_group.list_election_group_counting_results_query
    election_result = nodes.election.get_election_result_query

    # Candidates
    candidate = nodes.candidates.get_candidate_query

    # Pollbooks and registered voters
    voter = nodes.pollbook.get_voter_query
    voters_for_person = nodes.pollbook.find_voters_query
    search_voters = nodes.pollbook.search_voters_query

    # Users, persons and groups
    person = nodes.person.get_person_query
    search_persons = nodes.person.search_persons_query
    search_groups = nodes.group.search_groups_query
    viewer = nodes.person.get_current_viewer_query
    person_for_voter = nodes.person.get_person_for_voter_query

    # Votes
    votes_for_person = nodes.votes.find_votes_query

    # MasterKeys
    master_keys = nodes.privkeys_backup.list_active_master_keys_query
