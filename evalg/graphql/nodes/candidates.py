"""
GraphQL ObjectTypes for candidates and candidate lists.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.election_list
import evalg.models.candidate
from evalg.utils import convert_json
from evalg.graphql.nodes.utils.permissions import (
    permission_controller,
    permission_controlled_default_resolver,
    can_manage_election_list,
)
from evalg.graphql.nodes.utils.base import get_current_user, get_session


#
# Query
#
@permission_controller.control_object_type
class ElectionList(graphene_sqlalchemy.SQLAlchemyObjectType):
    """
    A list of candidates in a given election.
    """
    class Meta:
        model = evalg.models.election_list.ElectionList
        default_resolver = permission_controlled_default_resolver


def resolve_candidate_list_by_id(_, info, **args):
    session = get_session(info)
    return session.query(evalg.models.election_list.ElectionList).get(
        args['id'])


get_candidate_list_query = graphene.Field(
    ElectionList,
    resolver=resolve_candidate_list_by_id,
    id=graphene.Argument(graphene.UUID, required=True))


@permission_controller.control_object_type
class Candidate(graphene_sqlalchemy.SQLAlchemyObjectType):
    """
    A candidate that may appear in a given election.
    """
    class Meta:
        model = evalg.models.candidate.Candidate
        default_resolver = permission_controlled_default_resolver

    @permission_controller
    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)


def resolve_candidate_by_id(self, info, **args):
    session = get_session(info)
    return session.query(evalg.models.candidate.Candidate).get(args['id'])


get_candidate_query = graphene.Field(
    Candidate,
    resolver=resolve_candidate_by_id,
    id=graphene.Argument(graphene.UUID, required=True))


#
# Mutations
#


class AddPrefElecCandidate(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **args):
            return AddPrefElecCandidate(ok=False)
        meta = {'gender': args.get('gender')}
        candidate = evalg.models.candidate.Candidate(
            name=args.get('name'),
            meta=meta,
            list_id=args.get('list_id'),
            information_url=args.get('information_url'))
        session.add(candidate)
        session.commit()
        return AddPrefElecCandidate(ok=True)


class UpdatePrefElecCandidate(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        gender = graphene.String(required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **args):
            return UpdatePrefElecCandidate(ok=False)

        candidate = session.query(
            evalg.models.candidate.Candidate).get(args.get('id'))
        candidate.name = args.get('name')
        candidate.meta['gender'] = args.get('gender')
        candidate.list_id = args.get('list_id')
        candidate.information_url = args.get('information_url')
        session.add(candidate)
        session.commit()
        return UpdatePrefElecCandidate(ok=True)


class CoCandidatesInput(graphene.InputObjectType):
    name = graphene.String(required=True)


class AddTeamPrefElecCandidate(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        co_candidates = graphene.List(CoCandidatesInput, required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **args):
            return AddTeamPrefElecCandidate(ok=False)
        meta = {'co_candidates': args.get('co_candidates')}
        candidate = evalg.models.candidate.Candidate(
            name=args.get('name'),
            meta=meta,
            list_id=args.get('list_id'),
            information_url=args.get('information_url'))
        session.add(candidate)
        session.commit()
        return AddTeamPrefElecCandidate(ok=True)


class UpdateTeamPrefElecCandidate(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)
        co_candidates = graphene.List(CoCandidatesInput, required=True)
        list_id = graphene.UUID(required=True)
        information_url = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        if not can_manage_election_list(session, user, **args):
            return UpdateTeamPrefElecCandidate(ok=False)
        candidate = session.query(
            evalg.models.candidate.Candidate).get(args.get('id'))
        candidate.name = args.get('name')
        candidate.meta['co_candidates'] = args.get('co_candidates')
        candidate.list_id = args.get('list_id')
        candidate.information_url = args.get('information_url')
        session.add(candidate)
        session.commit()
        return UpdateTeamPrefElecCandidate(ok=True)


class DeleteCandidate(graphene.Mutation):
    """
    Delete a single candidate by id
    """
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        session = get_session(info)
        user = get_current_user(info)
        candidate = session.query(evalg.models.candidate.Candidate).get(
            args.get('id')
        )
        args['list_id'] = candidate.list_id
        if not can_manage_election_list(session, user, **args):
            return DeleteCandidate(ok=False)
        session.delete(candidate)
        session.commit()
        return DeleteCandidate(ok=True)
