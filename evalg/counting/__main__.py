# -*- coding: utf-8 -*-
"""
CLI entry point for the evalg.counting package

python -m evalg.counting --count <path to decrypted vote-xxx.zip>
"""
import argparse
import logging
import sys

from evalg.counting.count import Counter
from evalg.counting.legacy import (EvalgLegacyElection,
                                   EvalgLegacyInvalidBallot,
                                   EvalgLegacyInvalidFile)


if __name__ == '__main__':
    DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
    DEFAULT_LOG_LEVEL = logging.DEBUG
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)
    parser = argparse.ArgumentParser(
        description='The following options are available')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--count',
        action='store_true',
        dest='count',
        default=False,
        help='Perform a count')
    group.add_argument(
        '--dump',
        action='store_true',
        dest='dump',
        default=False,
        help='Create a text version of the election data')
    parser.add_argument(
        '-a', '--alternative-paths',
        action='store_true',
        dest='alternative_paths',
        default=False,
        help='Calculate all alternative election paths in case of drawing')
    parser.add_argument(
        'electionfile',
        metavar='<filename>',
        type=str,
        help='the election file (votes-XYZ.zip)')
    args = parser.parse_args()
    try:
        legacy_election = EvalgLegacyElection(args.electionfile)
        logger.debug("Adding legacy election: %s", legacy_election)
        counter = Counter(legacy_election,
                          legacy_election.ballots,
                          args.alternative_paths)
        if args.dump:
            print(counter.dumps())
        if args.count:
            election_count_tree = counter.count()
            election_count_tree.print_summary()  # debug
    except EvalgLegacyInvalidBallot as e:
        logger.error("Invalid ballot: %s", e)
        sys.exit(1)
    except EvalgLegacyInvalidFile:
        logger.error("Missing or invalid election-file: %s", args.electionfile)
        sys.exit(1)
    except Exception as e:
        logger.critical("Unhandled error: %s", e)
        sys.exit(1)
    sys.exit(0)
