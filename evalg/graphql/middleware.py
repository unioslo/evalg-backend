import logging
import time

from flask import current_app
from graphql import GraphQLError

logger = logging.getLogger(__name__)


class Timer(object):
    def __init__(self, operation, field):
        self.start = time.time()
        self.operation = operation
        self.field = field

    def get_millis(self):
        return round((time.time() - self.start) * 1000, 2)

    def log_time(self, result_or_error):
        logger.debug('promise for %s on %s resolved in %d ms',
                     self.operation, self.field, self.get_millis())
        return result_or_error

from evalg.authentication import user

def timing_middleware(next, root, info, **args):
    """
    Middleware component that logs the time it takes to resolve a promise.
    """
    if root is None:
        timer = Timer(info.operation.operation, info.field_name)
        return next(root, info, **args).then(timer.log_time,
                                             timer.log_time)
    return next(root, info, **args)


class ResultLogger(object):
    def __init__(self, operation, field):
        self.operation = operation
        self.field = field

    def log_promise(self, promise):
        logger.debug("promise for %s on %s: %r",
                     self.operation, self.field, promise)

    def log_success(self, result):
        logger.debug("promise fulfilled for %s on %s",
                     self.operation, self.field)
        return result

    def log_error(self, error):
        logger.error("promise rejected for %s on %s: %s",
                     self.operation, self.field, error, exc_info=error)
        return error


def logging_middleware(next, root, info, **args):
    """
    Middleware component that logs the result from resolving a promise.
    """
    if root is None:
        log_promise, log_success, log_error = True, True, True
    else:
        log_promise, log_success, log_error = False, False, True
    handler = ResultLogger(info.operation.operation, info.field_name)
    promise = next(root, info, **args).then(
        handler.log_success if log_success else None,
        handler.log_error if log_error else None)
    if log_promise:
        handler.log_promise(promise)
    return promise


def auth_middleware(next, root, info, **args):
    if root is None:
        # TBD: should we accept anonymous requests?
        # Logged in user available in info.context['user']

        # Look up user info here, then do a check on each type of query
        # and see if the user has proper authorization
        if info.field_name == 'electionList':
            current_app.logger.debug('Checking election authorization')
            # Plug in auth check for electionlist here, and stop middleware
            # chain if auth check fails.
            return next(root, info, **args)
    return next(root, info, **args)
