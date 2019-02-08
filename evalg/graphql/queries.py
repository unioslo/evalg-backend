"""
Queries for the evalg GraphQL API.
"""

import graphene

from . import nodes


class ElectionQuery(graphene.ObjectType):

    # Elections and election groups
    election_groups = nodes.election_group.list_election_groups_query
    election_group = nodes.election_group.get_election_group_query
    election_template = nodes.election_group.get_election_template_query
    elections = nodes.election.list_elections_query
    election = nodes.election.get_election_query

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

    # Users, persons and groups
    persons = nodes.person.list_persons_query
    person = nodes.person.get_person_query
    search_person = nodes.person.search_persons_query
    search_group = nodes.group.search_groups_query
    viewer = nodes.person.get_current_viewer_query
