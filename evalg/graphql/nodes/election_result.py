import graphene
import graphene_sqlalchemy

import evalg.models.election
import evalg.proc.count


class ElectionResult(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election_result.ElectionResult


def resolve_election_result_by_id(_, info, **args):
    return ElectionResult.get_query(info).get(args['id'])


get_election_group_count_query = graphene.Field(
    ElectionResult,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_result_by_id)

# Get all election results is disabled as there should be no need for it.
# def resolve_election_results(_, info):
#     return ElectionResult.get_query(info).all()
#
#
# list_election_results_query = graphene.List(
#     ElectionResult,
#     resolver=resolve_election_results
# )
