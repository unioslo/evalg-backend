#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Request ID tools. """
import logging
import uuid
from flask import request, has_request_context


def generate_request_id():
    """ Generates a random request UUID. """
    return str(uuid.uuid4())


def get_request_id():
    """ Gets the current request ID. """
    return request.headers.get('X-Request-ID', 'no-id')


def init_app(app):
    """ Sets header name and adds middleware. """
    app.config.setdefault('REQUEST_ID_HEADER', 'X-Request-ID')
    app.wsgi_app = RequestIDMiddleware(app.wsgi_app,
                                       app.config['REQUEST_ID_HEADER'])


class RequestIDMiddleware(object):
    def __init__(self, app, request_id_header):
        self.app = app
        self.request_id_header = request_id_header

    def __call__(self, environ, start_response):
        request_id = generate_request_id()
        environ["HTTP_X_REQUEST_ID"] = request_id

        def new_start_response(status, headers, exc_info=None):
            headers.append(('X-Request-ID', request_id))
            return start_response(status, headers, exc_info)
        return self.app(environ, new_start_response)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        """ Logging filter that adds the request ID to the log record. """
        record.request_id = get_request_id() if has_request_context() else ''
        return True
