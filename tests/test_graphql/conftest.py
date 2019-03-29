import pytest

from graphene.test import Client

from evalg.graphql import schema


@pytest.fixture(scope="session")
def client():
    return Client(schema)
