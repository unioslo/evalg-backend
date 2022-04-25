"""
Non graphql api endpoints 
"""

from . import health


def init_app(app):
    health.init_api(app)
