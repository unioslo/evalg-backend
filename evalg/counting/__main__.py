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
from evalg.counting import standalone


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
        '--count-legacy',
        action='store_true',
        dest='count_legacy',
        default=False,
        help='Perform a legacy count')
    parser.add_argument(
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
        '-p', '--protocol-file',
        metavar='<filename>',
        type=str,
        default='',
        dest='protocol_file',
        help=('Optional .txt file to store the protocol in '
              '(default: print to stdout)'))
    parser.add_argument(
        'electionfile',
        metavar='<filename>',
        type=str,
        help=('the election file (.json for --count and '
              'votes-XYZ.zip for --count-lagacy)'))
    args = parser.parse_args()
    try:
        if args.count:
            election = standalone.Election(args.electionfile)
            logger.debug("Adding standalone election: %s", election)
        if args.count_legacy:
            election = EvalgLegacyElection(args.electionfile)
            logger.debug("Adding legacy election: %s", election)
        if args.count_legacy or args.count:
            counter = Counter(election,
                              election.ballots,
                              args.alternative_paths)
            if args.dump:
                print(counter.dumps(), flush=True)
                sys.exit(0)
            election_count_tree = counter.count()
            election_count_tree.print_summary()  # debug
            # print(election_count_tree.default_path.get_result().to_json())
            # print(election_count_tree.default_path.get_protocol().to_json())
            path_protocol = election_count_tree.default_path.get_protocol()
            if args.protocol_file:
                with open(args.protocol_file, 'w', encoding='utf-8') as fp:
                    fp.write(path_protocol.render())
            else:
                print(path_protocol.render())
    except (EvalgLegacyInvalidBallot, standalone.InvalidBallotException) as e:
        logger.error("Invalid ballot: %s", e)
        sys.exit(1)
    except (EvalgLegacyInvalidFile, standalone.InvalidFileException):
        logger.error("Missing or invalid election-file: %s", args.electionfile)
        sys.exit(1)
    except Exception as e:
        logger.critical("Unhandled error: %s", e)
        sys.exit(1)
    sys.exit(0)
