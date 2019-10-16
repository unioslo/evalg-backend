from evalg.graphql.nodes.utils import permissions
from evalg.graphql.nodes.election import Election, ElectionResult
from evalg.graphql.nodes.election_group import (ElectionGroup,
                                                ElectionGroupCount)
from evalg.graphql.nodes.candidates import Candidate, ElectionList
from evalg.graphql.nodes.privkeys_backup import MasterKey
from evalg.graphql.nodes.pollbook import Pollbook, Voter, CensusFileImport
from evalg.graphql.nodes.person import Person
from evalg.graphql.nodes.votes import Vote
from evalg.graphql.nodes.group import Group

controlled_object_types = {
    'ElectionGroup': ElectionGroup,
    'Election': Election,
    'ElectionGroupCount': ElectionGroupCount,
    'ElectionResult': ElectionResult,
    'ElectionList': ElectionList,
    'Candidate': Candidate,
    'MasterKey': MasterKey,
    'Person': Person,
    'Voter': Voter,
    'Vote': Vote,
    'Pollbook': Pollbook,
    'Group': Group,
    'CensusFileImport': CensusFileImport,
}


def test_object_types_permission_controlled(app):
    """
    Should fail if an object type registered in default_config.PERMISSIONS
    lacks permission control on any of its fields.
    """
    controlled_fields = permissions.permission_controller.controlled_fields
    PERMISSIONS = app.config.get('PERMISSIONS')

    print(controlled_fields)

    for object_type_name in PERMISSIONS.keys():
        object_type = controlled_object_types[object_type_name]
        for attr_name in dir(object_type):
            if len(attr_name) > 7:
                if attr_name[:7] == 'resolve':
                    if not attr_name[8:] == 'id':
                        assert (attr_name in controlled_fields[
                            object_type_name])
        assert (object_type._meta.default_resolver.__name__ ==
                permissions.permission_controlled_default_resolver.__name__)
