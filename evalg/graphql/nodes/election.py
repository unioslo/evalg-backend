"""The GraphQL Election ObjectType."""
import pytz

import graphene
from graphene.types.generic import GenericScalar

import graphene_sqlalchemy

import evalg.models.election
from evalg.graphql.nodes.utils.base import get_current_user, get_session
from evalg.graphql.nodes.votes import (resolve_election_count_by_id,
                                       ElectionVoteCounts)
from evalg.graphql.nodes.utils.permissions import (
    permission_controller,
    permission_controlled_default_resolver,
    can_manage_election,
)
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

@permission_controller.control_object_type
class Election(graphene_sqlalchemy.SQLAlchemyObjectType):
    """Election class"""
    class Meta:
        model = evalg.models.election.Election
        default_resolver = permission_controlled_default_resolver

    @permission_controller
    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)

    is_ongoing = graphene.Boolean()
    pollbooks = graphene.List(pollbook.Pollbook)
    vote_count = graphene.Field(lambda: ElectionVoteCounts)

    @permission_controller
    def resolve_vote_count(self, info):
        return resolve_election_count_by_id(None, info, id=self.id)


@permission_controller.control_object_type
class ElectionResult(graphene_sqlalchemy.SQLAlchemyObjectType):
    """ElectionResult class"""
    class Meta:
        model = evalg.models.election_result.ElectionResult
        default_resolver = permission_controlled_default_resolver

    ballots_with_metadata = graphene.Field(GenericScalar)

    @permission_controller
    def resolve_ballots_with_metadata(self, info):
        ballots_with_metadata = {}

        meta = {}
        meta['election_id'] = str(self.election.id)
        meta['election_name'] = self.election.name
        meta['election_type'] = self.election.type_str
        meta['start'] = self.election.start.astimezone(
            pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S')
        meta['end'] = self.election.end.astimezone(
            pytz.timezone('Europe/Oslo')).strftime('%Y-%m-%d %H:%M:%S')
        if self.election.type_str == 'uio_stv':
            meta['num_regular'] = self.election.num_choosable
            meta['num_substitutes'] = self.election.num_substitutes
        ballots_with_metadata['meta'] = meta

        pollbook_names = {}
        for pbook in self.election.pollbooks:
            pollbook_names[str(pbook.id)] = pbook.name
        ballots_with_metadata['pollbook_names'] = pollbook_names

        if (
                self.election.meta['candidate_type'] == "single" or
                self.election.meta['candidate_type'] == "single_team"
        ):
            candidate_names = {}
            for candidate in self.election.lists[0].candidates:
                candidate_names[str(candidate.id)] = candidate.name
            ballots_with_metadata['candidate_names'] = candidate_names

        if self.election.meta['candidate_type'] == "party_list":
            # TODO after implementing list elections:
            # Handle this case according to how list and candidate names are
            # stored, and according to what is needed to "decode" UUIDs in
            # party_list ballots.
            # This might work:
            list_names = {}
            candidate_names = {}
            for election_list in self.election.lists:
                list_names[str(election_list.id)] = election_list.name
                for candidate in election_list.candidates:
                    candidate_names[str(candidate.id)] = candidate.name
            ballots_with_metadata['list_names'] = list_names
            ballots_with_metadata['candidate_names'] = candidate_names
        quotas = []
        for quota_group in self.election.quotas:
            quotas.append(
                {'name': quota_group.name,
                 'members': [str(m.id) for m in quota_group.members]})
        ballots_with_metadata['quotas'] = quotas

        ballots_with_metadata['ballots'] = self.ballots

        return convert_json(ballots_with_metadata)

    @permission_controller
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
                election = session.query(
                    evalg.models.election.Election).get(e['id'])

                if not can_manage_election(session, user, election):
                    return UpdateVotingPeriods(ok=False)
                election.start = elections[0].start
                election.end = elections[0].end
                session.add(election)
        else:
            for e in elections:
                election = session.query(
                    evalg.models.election.Election).get(e['id'])
                if not can_manage_election(session, user, election):
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
            election = session.query(
                evalg.models.election.Election).get(e['id'])
            if not can_manage_election(session, user, election):
                return UpdateVotingPeriods(ok=False)
            election.mandate_period_start = e.mandate_period_start
            election.mandate_period_end = e.mandate_period_end
            election.contact = e.contact
            election.information_url = e.information_url
            session.add(election)

        session.commit()
        return UpdateVoterInfo(ok=True)
