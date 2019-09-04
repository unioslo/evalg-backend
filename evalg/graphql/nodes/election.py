"""
The GraphQL Election ObjectType.
"""
import graphene
from graphene.types.generic import GenericScalar

import graphene_sqlalchemy

import evalg.models.election
from evalg.graphql.nodes.base import get_current_user, get_session
from evalg.graphql.nodes.votes import (resolve_election_count_by_id,
                                       ElectionVoteCounts)
from evalg.authorization import permissions
from evalg.utils import convert_json

from . import pollbook
from .. import types

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   elsewhere. The business logic of these operations does not belong in
#   GraphQL mutations.


#
# Query
#


class Election(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election.Election
        default_resolver = permissions.permission_controlled_default_resolver

    @permissions.permission_control_field
    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)

    is_ongoing = graphene.Boolean()
    pollbooks = graphene.List(pollbook.PollBook)
    vote_count = graphene.Field(lambda: ElectionVoteCounts)

    @permissions.permission_control_field
    def resolve_vote_count(self, info):
        return resolve_election_count_by_id(None, info, id=self.id)


def resolve_elections_by_fields(_, info):
    return Election.get_query(info).all()


def resolve_election_by_id(_, info, **args):
    return Election.get_query(info).get(args['id'])


list_elections_query = graphene.List(
    Election,
    resolver=resolve_elections_by_fields)

get_election_query = graphene.Field(
    Election,
    resolver=resolve_election_by_id,
    id=graphene.Argument(graphene.UUID, required=True))


class ElectionResult(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election_result.ElectionResult
        default_resolver = permissions.permission_controlled_default_resolver

    ballots_with_metadata = graphene.Field(GenericScalar)

    @permissions.permission_control_field
    def resolve_ballots_with_metadata(self, info):
        ballots_with_metadata = dict()

        pollbook_names = dict()
        for pbook in self.election.pollbooks:
            pollbook_names[str(pbook.id)] = pbook.name
        ballots_with_metadata['pollbook_names'] = pollbook_names

        if (
                self.election.meta['candidate_type'] == "single" or
                self.election.meta['candidate_type'] == "single_team"
        ):
            candidate_names = dict()
            for candidate in self.election.lists[0].candidates:
                candidate_names[str(candidate.id)] = candidate.name
            ballots_with_metadata['candidate_names'] = candidate_names

        if (self.election.meta['candidate_type'] == "party_list"):
            # TODO after implementing list elections:
            # Handle this case according to how list and candidate names are
            # stored, and according to what is needed to "decode" UUIDs in
            # party_list ballots.
            # This might work:
            list_names = dict()
            candidate_names = dict()
            for list in self.election.lists:
                list_names[str(list.id)] = list.name
                for candidate in list.candidates:
                    candidate_names[str(candidate.id)] = candidate.name
            ballots_with_metadata['list_names'] = list_names
            ballots_with_metadata['candidate_names'] = candidate_names

        ballots_with_metadata['ballots'] = self.ballots

        return convert_json(ballots_with_metadata)

    @permissions.permission_control_field
    def resolve_election_protocol(self, info):
        return self.election_protocol_text


def resolve_election_result_by_id(_, info, **args):
    return ElectionResult.get_query(info).get(args['id'])


get_election_result_query = graphene.Field(
    ElectionResult,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_result_by_id)


#
# Mutations
#

# TODO:
#   Could we rename some of these to something more sensible?
#   # *UpdateVotingPeriods* -> *UpdateElectionPeriods*
#   # *UpdateVoterInfo* -> *UpdateElectionInfo*

# TODO:
#   Do these mutations really need to deal with multiple elections in the
#   input?  Isn't there some GraphQL syntact to do multiple mutations in a
#   single request?


class ElectionVotingPeriodInput(graphene.InputObjectType):
    """
    Start and end datetime input for an election.
    """
    id = graphene.UUID(required=True)
    start = types.DateTime(required=True)
    end = types.DateTime(required=True)


class UpdateVotingPeriods(graphene.Mutation):
    """
    Update the voting periods for an election.
    """
    class Arguments:
        elections = graphene.List(ElectionVotingPeriodInput, required=True)
        has_multiple_times = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        elections = args.get('elections')
        if not args.get('has_multiple_times'):
            # TODO: Do we need this? Could we not just send a datetime input
            # for each election?
            for e in elections:
                election = evalg.models.election.Election.query.get(e['id'])
                if not permissions.can_manage_election(session, user, election):
                    return UpdateVotingPeriods(ok=False)
                election.start = elections[0].start
                election.end = elections[0].end
                session.add(election)
        else:
            for e in elections:
                election = evalg.models.election.Election.query.get(e['id'])
                if not permissions.can_manage_election(session, user, election):
                    return UpdateVotingPeriods(ok=False)
                election.start = e.start
                election.end = e.end
                session.add(election)
        session.commit()
        return UpdateVotingPeriods(ok=True)


class ElectionVoterInfoInput(graphene.InputObjectType):
    """
    Mandate period and contact info input for elections.
    """
    id = graphene.UUID(required=True)
    mandate_period_start = types.Date(required=True)
    mandate_period_end = types.Date(required=True)
    contact = graphene.String()
    information_url = graphene.String()


class UpdateVoterInfo(graphene.Mutation):
    """
    Update the mandate period and contact information for elections..
    """
    class Arguments:
        elections = graphene.List(ElectionVoterInfoInput, required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        elections = args.get('elections')
        for e in elections:
            election = evalg.models.election.Election.query.get(e['id'])
            if not permissions.can_manage_election(session, user, election):
                return UpdateVotingPeriods(ok=False)
            election.mandate_period_start = e.mandate_period_start
            election.mandate_period_end = e.mandate_period_end
            election.contact = e.contact
            election.information_url = e.information_url
            session.add(election)

        session.commit()
        return UpdateVoterInfo(ok=True)
