import io
import pytest

from graphene.test import Client
from werkzeug.test import EnvironBuilder

from evalg.graphql import schema


@pytest.fixture(scope="session")
def client():
    return Client(schema)


def generate_census_file_builder(ids, file_ending, linebrake='\n'):
    """Generate census test files."""
    return EnvironBuilder(method='POST', data={
        'file': (io.BytesIO(linebrake.join(ids).encode('utf-8')),
                 'usernames.{}'.format(file_ending))})


@pytest.fixture
def uids():
    """A list of uids."""
    return ['pederaas', 'martekir', 'larsh', 'hansta']


@pytest.fixture
def feide_ids(uids):
    """A list of feide ids."""
    return ['{}@uio.no'.format(x) for x in uids]


@pytest.fixture
def feide_id_plane_text_census_builder(feide_ids):
    """Plain text census file of feide ids."""
    return generate_census_file_builder(feide_ids, 'txt')