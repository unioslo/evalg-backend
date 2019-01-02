# -*- coding: utf-8 -*-
from evalg.models.ou import OrganizationalUnit
from flask import current_app as app

def election_template_builder():
    ou_tags = app.config.get('OU_TAGS')
    ou_lists = dict()
    for tag in ou_tags:
        ou_lists[tag] = list()
    for ou in OrganizationalUnit.query.all():
        if ou.tag in ou_tags:
            ou_dict = dict()
            for attr in ['id', 'name', 'tag', 'external_id']:
                if attr != 'name':
                    ou_dict[attr] = str(getattr(ou, attr))
                else:
                    ou_dict[attr] = getattr(ou, attr)
            ou_lists[ou.tag].append(ou_dict)
    election_template = dict()
    election_template['template_root'] = app.config.get('ROOT_NODE')
    election_template['ou_lists'] = ou_lists
    return election_template
