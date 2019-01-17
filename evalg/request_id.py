""" Utilities for processing and logging a request id. """
import logging
import uuid

from flask import _request_ctx_stack
from flask import current_app
from flask import has_request_context
from flask import request

logger = logging.getLogger(__name__)
request_id_key = __name__ + ':request_id'


def generate_request_id():
    """ Generate a random request uuid. """
    return str(uuid.uuid4())


def set_request_id(request_id):
    """ Set request_id in request context. """
    ctx = _request_ctx_stack.top
    setattr(ctx, request_id_key, request_id)


def get_request_id():
    """ Get request_id from request context. """
    ctx = _request_ctx_stack.top
    return getattr(ctx, request_id_key, None)


class RequestId(object):
    """ Update request context with a request_id. """

    CONFIG_REQUEST_HEADER_KEY = 'REQUEST_ID_HEADER'
    CONFIG_REQUEST_HEADER_DEFAULT = 'X-Request-Id'
    CONFIG_RESPONSE_HEADER_KEY = 'RESPONSE_ID_HEADER'
    CONFIG_RESPONSE_HEADER_DEFAULT = 'X-Request-Id'

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    @property
    def _request_header(self):
        return current_app.config[self.CONFIG_REQUEST_HEADER_KEY]

    @property
    def _response_header(self):
        return current_app.config[self.CONFIG_RESPONSE_HEADER_KEY]

    def init_app(self, app):
        app.config.setdefault(self.CONFIG_REQUEST_HEADER_KEY,
                              self.CONFIG_REQUEST_HEADER_DEFAULT)
        app.config.setdefault(self.CONFIG_RESPONSE_HEADER_KEY,
                              self.CONFIG_RESPONSE_HEADER_DEFAULT)

        @app.before_request
        def update_context_with_id():
            request_id = (request.headers.get(self._request_header)
                          or generate_request_id())
            set_request_id(request_id)
            logger.debug("request=%r", request)

        @app.after_request
        def update_response_with_id(resp):
            resp.headers[self._response_header] = get_request_id()
            logger.debug("response=%r", resp)
            return resp


class RequestIdFilter(logging.Filter):
    """ Logging filter that adds the request id to log records. """

    def filter(self, record):
        if has_request_context():
            request_id = get_request_id()
        else:
            request_id = None
        record.request_id = request_id
        return True
