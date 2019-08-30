from evalg.authorization.permissions import (
    permission_control_decorate,
    permission_controlled_default_resolver
)
from evalg.graphql.nodes.election_group import (
    ElectionGroup
)


def test_election_group_fields_permission_controlled():
    for attr_name in dir(ElectionGroup):
        if len(attr_name) > 7:
            if attr_name[:7] == 'resolve':
                if attr_name[8:] == 'id':
                    continue
                assert (attr_name in permission_control_decorate.decorated_resolvers)

    assert (ElectionGroup._meta.default_resolver.__name__ ==
            permission_controlled_default_resolver.__name__)
