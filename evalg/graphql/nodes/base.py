"""
Common GraphQL objects and functionality.
"""
import graphene


def get_session(info):
    return info.context.get('session')


class MutationResponse(graphene.ObjectType):
    """Generic mutation response"""
    success = graphene.Boolean()
    code = graphene.String()
    message = graphene.String()
