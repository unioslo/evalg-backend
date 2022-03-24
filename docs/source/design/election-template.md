# Valgtemplater

Valgtemplatene definerer hvilke valg som kan velges, og hvilke regler som skal brukes til stemming og opptelling av disse. Templatet definerer et tre, med variabelen ``ROOT_NODE`` som rotnoden. Nodene i treet definerer ulike valg for valgadministrator. Løvnodene definerer et spesifikt valg med tilhørende innstillinger.

## Valgtypenoder

Nodene definerer valg som dukker opp på "opprett nytt valg" siden. Under er et eksempel:
```json
{
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
            ]
        },
    ]
}
```

* ``options`` definerer en liste av valg.

* ``settings``
  
  Innstillinger for valget. Mulige innstillinger er:
  * ``template``

    Om navnet på valget skal genereres utfra valgt enhet.

  * ``ou_tag``

    Hvilke ``ou_tag`` som skal brukes til filtrering av enheter.

  * ``template_name``

    Navn på templaten som skal brukes

  *

* ``next_nodes``

  Definerer hva neste steg på "opprett valg" siden skal være. Dette er også en valgnode.

* ``set_election_name``: ``Boolean``

  Om navn skal oppgis manuelt.

## Valgoppsettsnoder

Definerer hvilke innstillinger som skal være satt for et valg.
Type valg, hvilke grupper som skal være definert osv.

```json
'board_leader': {
    'group_type': 'single_election',
    'rule_set': election_rule_sets['khio_teams'],
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
                'weight': 60,
            },
            {
                'name': grp_names['tech_adm_staff'],
                'weight': 20,
            },
            {
                'name': grp_names['students'],
                'weight': 20,
            }
        ],
    }]
},
```


## Valgreglenoder

``election_rule_sets`` definerer regelsettet for et valgordningene.

Under er et eksempel på en "valgregelnode". 

```json
}
  'uio_stv': {
      'candidate_type': 'single',
      'candidate_rules': {'seats': 1,
                          'substitutes': 2,
                          'candidate_gender': True},
      'ballot_rules': {
          'voting': 'rank_candidates',
          'votes': 'all',
      },
      'counting_rules': {
          'method': 'uio_stv',
          'affirmative_action': ['gender_40'],
      },
  }
}
```

### candidate_type

Bestemmer hvilken type kandidat som skal velges.
Verdien brukes til å vise frem ulike stemmesider.

* single

  Stemme på enkeltperson.

* single_team

  Stemme med medkandidat. Brukes av rektor-/dekanvalg.

* party_list

  Stemme for listevalg.
  

### candidate_rules

Bestemmer regler for kandidater.

Følgende verdier er mulig

* seats: ``Int``

  Antall plasser som skal velges. Kan i noen tilfeller overstyres av valgadmin.

* substitutes: ``Int``

  Antall varaplasser som skal velges. Kan i noen tilfeller overstyre av valgadmin

* candidate_gender: ``Boolean``

  Skal kjønn spesifiseres for kandidatene? Brukes til kvotering.

### ballot_rules

Definerer regler for hva som er lov med

* voting: ``'no_rank'`` | ``'rank_candidate'`` | ``'list'``

  Bestemmer hvordan en skal stemme på kandidater.
  * ``no_rank``: Velg en eller flere kandidater. Ingen rangering.
  * ``rank_candidate``: Ranger kandidatene i preferert rekkefølge.
  * ``list``: Listevalg.

* votes: ``Int`` | ``'all'`` | ``'nr_of_seats'``

  Bestemmer hvor mange kandidater en kan stemme på

* allow_blank: ``Boolean``

  Bestemmer om valget skal tillater blanke stemmer.

* delete_candidate: ``Boolean``

  Listevalg. Bestemmer om det er det lov å fjerne kandidater fra en liste.

* cumulate: ``Boolean``

  Listevalg. Bestemmer om det er lov å kumulere kandidater.

* alter_priority: ``Boolean``

  Listevalg. Bestemmer om det er mulig å endre på rekkefølgen på kandidatene i en liste.

* other_list_candidate_votes: ``Boolean``

  Listevalg. Bestemmer om det skal være mulig å ha med slengere fra andre lister.

### counting_rules

Definerer regler for opptelling.

* method: ``'uio_stv'`` | ``'uio_mv'`` | ``'mntv'`` | ``'poll'`` | ``'sainte_lague'``

  Hvilken metode skal benyttes ved opptelling. TODO: Legg til nye for listeopptelling

* affirmative_action: ``['gender_40]``
  
  Hvilke kvoteringsregler skal benyttes ved opptelling.
  
* first_divisor: ``Int``

  Første delingstall

* precumulate: ``Int``

  Usikker?

* list_votes: ``'seats'`` | ``'nr_of_seats'``
  
  Hvor mange listestemmer en liste har.

* other_list_candidate_votes: ``Boolean``
  
  Tillat slengere
  

## OU-tags

Det er definert opp 4 "OU-tags" (``'root'``, ``'faculty'``, ``'department'``, ``'unit'``). Tanken med disse var å tagge de ulike enhetene utifra om de var en fakultet, institutt osv, og bruke denne informasjonen til å kun vise frem relevant enheter. 
