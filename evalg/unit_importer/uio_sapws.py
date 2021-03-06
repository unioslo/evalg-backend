from evalg.unit_importer.importer import UnitImporter

import logging

from collections import deque
from sap_client import SapClient

logger = logging.getLogger(__name__)


@UnitImporter.register('UIOSAPWS')
class UIOSAPWSImporter(UnitImporter):

    def __init__(self, config):
        super().__init__(config)

    def check_config(self):
        """Rudimentary config check"""
        if 'api_key' not in self.config:
            raise ValueError('UIOSPWS api_key missing from config')
        elif 'base_url' not in self.config:
            raise ValueError('UIOSPWS base_url missing from config')
        elif 'root_ou' not in self.config:
            raise ValueError('UIOSPWS root_ou missing from config')

    def get_units(self):
        """Generator returning units from SAPWS."""

        client = SapClient(
            self.config['base_url'],
            headers={'X-Gravitee-API-Key': self.config['api_key']})

        for unit in client.list_locations():
            u = {}

            if 'locationCode' in unit:
                u['external_id'] = unit['locationCode']
            elif 'locationId' in unit:
                u['external_id'] = str(unit['locationId'])
            else:
                logger.error('Ou is missing ou code.. skipping')
                continue

            if u['external_id'] == self.config['root_ou']:
                u['tag'] = 'root'
            else:
                u['tag'] = 'unit'

            if 'locationName' in unit:
                u['name'] = {}
                for lang, name in unit['locationName'].items():
                    if lang == '__metadata' or not name:
                        continue
                    elif 'longName' in name:
                        u['name'][lang] = name['longName']
                    elif 'mediumName' in name:
                        u['name'][lang] = name['mediumName']
                    elif 'shortName' in name:
                        u['name'][lang] = name['shortName']
                    elif 'acronym' in name:
                        u['name'][lang] = name['acronym']
                    else:
                        logger.error(
                            'OU: %s, Language %s defined, but no name found',
                            unit['locationId'],
                            lang)
                        continue
                if len(u['name']) == 0 or (
                    'en' not in u['name'] and
                        'nb' not in u['name']):
                    # No nb/en name, skipping
                    logger.error(
                        'OU: %s, No english or norwegian name found, skipping',
                        u['external_id'])
                    continue
                if 'en' not in u['name']:
                    logger.info(
                        'OU: %s, No English name. Using the Norwegian name',
                        u['external_id'])
                    u['name']['en'] = u['name']['nb']
                elif 'nb' not in u['name']:
                    logger.info(
                        'OU: %s, No Norwegian name. Using the English name',
                        u['external_id'])
                    u['name']['nb'] = u['name']['en']
                if 'nn' not in u['name']:
                    # The ou tree is missing nynorsk names, use bokmål for now
                    u['name']['nn'] = u['name']['nb']
            else:
                # Unit without name skipping
                logger.error(
                    'OU: %s, No language defined, skipping OU',
                    unit['locationId'],
                )
                continue

            yield u
