# coding: utf_8

ou_tags = ['root', 'faculty', 'department', 'unit']
""" The possible ou tags in use. """

###
# ELECTION RULESETS
# The rulesets used by the various supported election types should
# be defined here.
###

election_rule_sets = {
    # TBD: Versioning?
    # 'Preferansevalg' by UiO rules (normal)
    # TODO: How should we define single/multiple candidate lists?
    'uio_stv': {
        # Candidate is person, no co candidate
        'candidate_type': 'single',
        # which metadata to collect:
        # number of seats, number of subs, and gender for affirmative action
        'candidate_rules': {'seats': 1,
                            'substitutes': 2,
                            'candidate_gender': True},
        'ballot_rules': {
            # should rank the candidates
            'voting': 'rank_candidates',
            # no constraints in number of votes
            'votes': 'all',
        },
        'counting_rules': {
            'method': 'uio_stv',
            'affirmative_action': ['gender_40'],
        },
    },
    'uio_teams': {
        'candidate_type': 'single_team',
        'candidate_rules': {'seats': 1},
        'ballot_rules': {
            'voting': 'rank_candidates',
            'votes': 'all',
        },
        'counting_rules': {
            # method can not be decided until we know how many candidates the
            # election has. Candidates are not frozen until the election is
            # published.
            'method': None,
        },
    },
    'uio_sp_list': {
        'candidate_type': 'party_list',
        'candidate_rules': {'seats': 30},
        'ballot_rules': {
            'delete_candidate': True,
            'cumulate': True,
            'alter_priority': True,
            'number_of_votes': 'seats',
            'other_list_candidate_votes': True,
            'voting': 'list'
        },
        'counting_rules': {
            'method': 'sainte_lague',
            'first_divisor': 1,
            'precumulate': 1,
            'list_votes': 'seats',
            'other_list_candidate_votes': True
        }
    },
}
###
# GROUP NAMES
# Common names of groups in the organization.
# Sometimes we want separate elections for these groups if they are
# voting for representatives only from their own group, and sometimes we want
# to represent them as separate censuses in the same election, if their votes
# carry separate weights.
###
grp_names = {
    'tech_adm_staff': {
        'nb': 'Teknisk/administrativt ansatte',
        'nn': 'Teknisk/administrativt tilsette',
        'en': 'Technical and administrative staff',
    },
    'academic_staff': {
        'nb': 'Vitenskapelig ansatte',
        'nn': 'Vitskapeleg tilsette',
        'en': 'Academic staff',
    },
    'tmp_academic_staff': {
        'nb': 'Midlertidig vitenskapelige ansatte',
        'nn': 'Mellombels vitskapeleg tilsette',
        'en': 'Temporary academic staff',
    },
    'students': {
        'nb': 'Studenter',
        'nn': 'Studentar',
        'en': 'Students',
    }
}


###
# ELECTION GROUP TYPES
# The various types of elections that are supported.
###
election_group_types = {
    'board_leader': {
        'group_type': 'single_election',
        'rule_set': election_rule_sets['uio_teams'],
        'elections': [{
            'sequence': 'all',
            'name': None,
            'mandate_period': {
                'start': '--01-01',
                'duration': 'P4Y',
            },
            'voter_groups': [
                {
                    'name': grp_names['academic_staff'],
                    'weight': 53,
                },
                {
                    'name': grp_names['tech_adm_staff'],
                    'weight': 22,
                },
                {
                    'name': grp_names['students'],
                    'weight': 25,
                }
            ],
        }]
    },
    'board': {
        'group_type': 'multiple_elections',
        'rule_set': election_rule_sets['uio_stv'],
        'elections': [
            {
                'sequence': 'permanent_academic_staff',
                'mandate_period': {
                    'start': '--01-01',
                    'duration': 'P4Y',
                },
                'name': grp_names['academic_staff'],
                'voter_groups': [{
                    'name': grp_names['academic_staff'],
                    'weight': 100,
                }],
            },
            {
                'sequence': 'temp_academic_staff',
                'mandate_period': {
                    'start': '--01-01',
                    'duration': 'P1Y',
                },
                'name': grp_names['tmp_academic_staff'],
                'voter_groups': [{
                    'name': grp_names['tmp_academic_staff'],
                    'weight': 100,
                }],
            },
            {
                'sequence': 'tech_adm_staff',
                'mandate_period': {
                    'start': '--01-01',
                    'duration': 'P4Y',
                },
                'name': grp_names['tech_adm_staff'],
                'voter_groups': [{
                    'name': grp_names['tech_adm_staff'],
                    'weight': 100,
                }],
            },
            {
                'sequence': 'students',
                'mandate_period': {
                    'start': '--01-01',
                    'duration': 'P1Y',
                },
                'name': grp_names['students'],
                'voter_groups': [
                    {
                        'name': grp_names['students'],
                        'weight': 100,
                    },
                ],
            },
        ]
    },
    'parliament': {
        'group_type': 'single_election',
        'rule_set': election_rule_sets['uio_sp_list'],
        'elections': [{
            'sequence': 'all',
            'name': None,
            'mandate_period': {
                'start': '--07-01',
                'duration': 'P1Y',
            },
            'voter_groups': [
                {
                    'name': grp_names['students'],
                    'weight': 100,
                }
            ],
        }]
    },
}

###
# ELECTION GROUP TEMPLATES
# These are the defined templates.
# They should contain a dict <name> with the predefined name, which will
# get the OU_name injected when generating a new election, as well as
# a reference to the type of election.
###
ELECTION_GROUP_TEMPLATES = {
    'uio_principal': {
        'name': {
            'nb': 'Rektor ved {}',
            'nn': 'Rektor ved {}',
            'en': 'Rector at {}'
        },
        'settings': election_group_types['board_leader'],
    },
    'uio_dean': {
        'name': {
            'nb': 'Dekanat ved {}',
            'nn': 'Dekanat ved {}',
            'en': 'Dean at {}'
        },
        'settings': election_group_types['board_leader'],
    },
    'uio_department_leader': {
        'name': {
            'nb': 'Instituttledelse ved {}',
            'nn': 'Instituttleiar ved {}',
            'en': 'Department leader at {}'
        },
        'settings': election_group_types['board_leader'],
    },
    'uio_university_board': {
        'name': {
            'nb': 'Universitetsstyre ved {}',
            'nn': 'Universitetsstyre ved {}',
            'en': 'University board at {}',
        },
        'settings': election_group_types['board'],
    },
    'uio_faculty_board': {
        'name': {
            'nb': 'Fakultetsstyre ved {}',
            'nn': 'Fakultetsstyre ved {}',
            'en': 'Faculty board at {}',
        },
        'settings': election_group_types['board'],
    },
    'uio_department_board': {
        'name': {
            'nb': 'Instituttstyre ved {}',
            'nn': 'Instituttstyre ved {}',
            'en': 'Department board at {}',
        },
        'settings': election_group_types['board'],
    },
    'uio_student_parliament': {
        'name': {
            'nb': 'Studentparlament ved {}',
            'nn': 'Studentparlament ved {}',
            'en': 'Student parliament at {}',
        },
        'settings': election_group_types['parliament'],
    },
}


###
# UI TEMPLATE TREE SETTINGS
# These are various options that will be sent to the front_end.
# The options are rendered as a tree of choices, with a root node.
# In the root node, there can be any given number of initial options
# available, with each option containing an entry <next_nodes> that
# defines the following options to display.
# Every branch in the tree should generate the necessary settings in order
# to determine which type of election should be created, and in which OU
# the election is linked to.
###
select_ou_node = {
    'name': {
        'nb': 'Valgkrets',
        'nn': 'Valgkrets',
        'en': 'Constituency'
    },
    'search_in_ou_tree': True
}

board_leader_node = {
    'name': {
        'nb': 'Valg av',
        'nn': 'Valg av',
        'en': 'What to elect'
    },
    'options': [
        {
            'name': {
                'nb': 'Rektorat',
                'nn': 'Rektorat',
                'en': 'Rector'
            },
            'settings': {
                'ou_tag': 'root',
                'template_name': 'uio_principal'
            }
        },
        {
            'name': {
                'nb': 'Dekan/dekanat',
                'nn': 'Dekan/dekanat',
                'en': 'Dean',
            },
            'settings': {
                'ou_tag': 'unit',
                'template_name': 'uio_dean'
            }
        },
        {
            'name': {
                'nb': 'Instituttleder/-ledelse',
                'nn': 'Instituttleiar/-leiing',
                'en': 'Institute leader',
            },
            'settings': {
                'ou_tag': 'unit',
                'template_name': 'uio_department_leader'
            }
        },
    ]
}

board_node = {
    'name': {
        'nb': 'Valg av',
        'nn': 'Valg av',
        'en': 'What to elect'
    },
    'options': [
        {
            'name': {
                'nb': 'Universitetsstyre',
                'nn': 'Universitetsstyre',
                'en': 'University Board'
            },
            'settings': {
                'ou_tag': 'root',
                'template_name': 'uio_university_board'
            }
        },
        {
            'name': {
                'nb': 'Fakultetsstyre',
                'nn': 'Fakultetsstyre',
                'en': 'Faculty Board',
            },
            'settings': {
                'ou_tag': 'unit',
                'template_name': 'uio_faculty_board'
            }
        },
        {
            'name': {
                'nb': 'Instituttstyre',
                'nn': 'Instituttstyre',
                'en': 'Institute Board',
            },
            'settings': {
                'ou_tag': 'unit',
                'template_name': 'uio_department_board'
            }
        },
    ]
}

ROOT_NODE = {
    'name': {
        'nb': 'Valgordning',
        'nn': 'Valgordning',
        'en': 'Election'
    },
    'options': [
        {
            'name': {
                'en': 'Board leader',
                'nb': 'Styreleder',
                'nn': 'Styreleiar'
            },
            'settings': {
                'template': True,
            },
            'next_nodes': [
                board_leader_node,
                select_ou_node
            ]
        },
        {
            'name': {
                'en': 'Board',
                'nb': 'Styreorgan',
                'nn': 'Styreorgan'
            },
            'settings': {
                'template': True,
            },
            'next_nodes': [
                board_node,
                select_ou_node
            ]
        },
        {
            'name': {
                'en': 'Student parliament',
                'nb': 'Studentparlament',
                'nn': 'Studentparlament'
            },
            'settings': {
                'template': True,
                'ou_tag': 'root',
                'template_name': 'uio_student_parliament'
            }
        },
    ]
}
