import graphene
import graphene_sqlalchemy

import evalg.models.election
import evalg.proc.count
from evalg import db


class ElectionGroupCount(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        model = evalg.models.election_group_count.ElectionGroupCount


def resolve_election_group_count_by_id(_, info, **args):
    return ElectionGroupCount.get_query(info).get(args['id'])


get_election_group_count_query = graphene.Field(
    ElectionGroupCount,
    id=graphene.Argument(graphene.UUID, required=True),
    resolver=resolve_election_group_count_by_id)


def resolve_election_group_counts(_, info):
    return ElectionGroupCount.get_query(info).all()


list_election_group_count_query = graphene.List(
    ElectionGroupCount,
    resolver=resolve_election_group_counts
)
