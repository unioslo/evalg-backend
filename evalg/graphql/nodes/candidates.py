"""
GraphQL ObjectTypes for candidates and candidate lists.
"""
import graphene
import graphene_sqlalchemy

import evalg.models.election_list
import evalg.models.candidate
from evalg.utils import convert_json
from evalg import db


#
# Query
#

# TODO:
#   We need to rename ElectionList in our models to something more
#   representative. CandidateList, or Electables, or somethign like that.

# TODO:
#   We should use an explicit db session passed through the `info.context`
#   object, rather than relying on the builtin `Model.query`.
#   E.g. Model.get_query(info) -> info.context.session.query(Model)

# TODO:
#   All Queries and Mutations should be implemented using functionality from
#   evalg.candidates in order to show or mutate candidate lists or candidates.


class ElectionList(graphene_sqlalchemy.SQLAlchemyObjectType):
    """
    A list of candidates in a given election.
    """
    class Meta:
        model = evalg.models.election_list.ElectionList


def resolve_candidate_lists_by_fields(_, info, **args):
    return ElectionList.get_query(info).all()


def resolve_candidate_list_by_id(_, info, **args):
    return ElectionList.get_query(info).get(args['id'])


list_candidate_lists_query = graphene.List(
    ElectionList,
    resolver=resolve_candidate_lists_by_fields)


get_candidate_list_query = graphene.Field(
    ElectionList,
    resolver=resolve_candidate_list_by_id,
    id=graphene.Argument(graphene.UUID, required=True))


class Candidate(graphene_sqlalchemy.SQLAlchemyObjectType):
    """
    A candidate that may appear in a given election.
    """
    class Meta:
        model = evalg.models.candidate.Candidate

    def resolve_meta(self, info):
        if self.meta is None:
            return None
        return convert_json(self.meta)


def resolve_candidates_by_fields(_, info):
    return Candidate.get_query(info).all()


def resolve_candidate_by_id(self, info, **args):
    return Candidate.get_query(info).get(args['id'])


list_candidates_query = graphene.List(
    Candidate,
    resolver=resolve_candidates_by_fields)

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
        meta = {'gender': args.get('gender')}
        candidate = evalg.models.candidate.Candidate(
            name=args.get('name'),
            meta=meta,
            list_id=args.get('list_id'),
            information_url=args.get('information_url'))
        db.session.add(candidate)
        db.session.commit()
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
        candidate = evalg.models.candidate.Candidate.query.get(args.get('id'))
        candidate.name = args.get('name')
        candidate.meta['gender'] = args.get('gender')
        candidate.list_id = args.get('list_id')
        candidate.information_url = args.get('information_url')
        db.session.add(candidate)
        db.session.commit()
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
        meta = {'co_candidates': args.get('co_candidates')}
        candidate = evalg.models.candidate.Candidate(
            name=args.get('name'),
            meta=meta,
            list_id=args.get('list_id'),
            information_url=args.get('information_url'))
        db.session.add(candidate)
        db.session.commit()
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
        candidate = evalg.models.candidate.Candidate.query.get(args.get('id'))
        candidate.name = args.get('name')
        candidate.meta['co_candidates'] = args.get('co_candidates')
        candidate.list_id = args.get('list_id')
        candidate.information_url = args.get('information_url')
        db.session.add(candidate)
        db.session.commit()
        return UpdateTeamPrefElecCandidate(ok=True)


class DeleteCandidate(graphene.Mutation):
    """
    Delete a single candidate by id
    """
    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, **args):
        candidate = evalg.models.candidate.Candidate.query.get(args.get('id'))
        db.session.delete(candidate)
        db.session.commit()
        return DeleteCandidate(ok=True)