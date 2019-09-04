"""
Common GraphQL objects and functionality.
"""
import graphene


def get_session(info):
    return info.context.get('session')


def get_current_user(info):
    return info.context.get('user')


class MutationResponse(graphene.ObjectType):
    """Generic mutation response"""
    success = graphene.Boolean()
    code = graphene.String()
    message = graphene.String()
