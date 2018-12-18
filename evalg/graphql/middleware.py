from flask import current_app
from graphql import GraphQLError
from time import time as timer


def timing_middleware(next, root, info, **args):
    if root is None:
        start = timer()
        return_value = next(root, info, **args)
        duration = timer() - start
        current_app.logger.debug(
            'Running query for: {field_name} - {duration} ms'.format(
                field_name=info.field_name,
                duration=round(duration * 1000, 2)
            )
        )
        return return_value
    return next(root, info, **args)


def auth_middleware(next, root, info, **args):
    if root is None:
        token_header = info.context.headers.get('Authorization')
        if token_header is None:
            raise GraphQLError('No Authorization header found.')
        token = token_header.split(' ')[1]
        # Look up user info here, then do a check on each type of query
        # and see if the user has proper authorization
        if info.field_name == 'electionList':
            current_app.logger.debug('Checking election authorization')
            # Plug in auth check for electionlist here, and stop middleware
            # chain if auth check fails.
            return next(root, info, **args)
    return next(root, info, **args)