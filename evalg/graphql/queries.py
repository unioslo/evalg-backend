"""
Queries for the evalg GraphQL API.
"""

import graphene

from . import nodes


class ElectionQuery(graphene.ObjectType):
    # Elections and election groups
    election_groups = nodes.election_group.list_election_groups_query
    election_group = nodes.election_group.get_election_group_query
    election_group_key_meta = nodes.election_group.get_election_key_meta_query
    election_template = nodes.election_group.get_election_template_query
    elections = nodes.election.list_elections_query
    election = nodes.election.get_election_query

    # Election results
    election_group_count = \
        nodes.election_group.get_election_group_count_query
    election_group_counting_results = \
        nodes.election_group.list_election_group_counting_results_query
    election_result = nodes.election.get_election_group_count_query

    # Candidates and candidate lists
    # TODO: rename *election_list(s)* to *candidate_list(s)*?
    election_lists = nodes.candidates.list_candidate_lists_query
    election_list = nodes.candidates.get_candidate_list_query
    candidates = nodes.candidates.list_candidates_query
    candidate = nodes.candidates.get_candidate_query

    # Pollbooks and registered voters
    pollbooks = nodes.pollbook.list_pollbooks_query
    pollbook = nodes.pollbook.get_pollbook_query
    voters = nodes.pollbook.list_voters_query
    voter = nodes.pollbook.get_voter_query
    voters_for_person = nodes.pollbook.find_voters_query
    search_voters = nodes.pollbook.search_voters_query

    # Users, persons and groups
    persons = nodes.person.list_persons_query
    person = nodes.person.get_person_query
    search_persons = nodes.person.search_persons_query
    search_groups = nodes.group.search_groups_query
    viewer = nodes.person.get_current_viewer_query
    person_for_voter = nodes.person.get_person_for_voter_query

    # Votes
    votes_for_person = nodes.votes.find_votes_query
