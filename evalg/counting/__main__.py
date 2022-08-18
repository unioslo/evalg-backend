# -*- coding: utf-8 -*-
"""
CLI entry point for the evalg.counting package

python -m evalg.counting --count-legacy <path to decrypted vote-xxx.zip>
python -m evalg.counting --count <path to .json ballot dump file>
"""
import argparse
import io
import logging
import os
import sys

from evalg.counting.algorithms import uitstv
from evalg.counting.count import Counter, ElectionCountTree
from evalg.counting.legacy import (EvalgLegacyElection,
                                   EvalgLegacyInvalidBallot,
                                   EvalgLegacyInvalidFile)
from evalg.counting import standalone


DEFAULT_LOG_FORMAT = "%(levelname)s: %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)


def main(args=None):
    """Main runtime"""
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
        '--uitstv',
        action='store_true',
        default=False,
        help='The election should be of type UiTSTV')
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
        '-i', '--interactive-drawing',
        action='store_true',
        dest='interactive_drawing',
        default=False,
        help='Prompt the user for input when drawing')
    parser.add_argument(
        '-p', '--protocol-file',
        metavar='<filename>',
        type=str,
        default='',
        dest='protocol_file',
        help=('Optional .txt file to store the protocol in '
              '(default: print to stdout)'))
    parser.add_argument(
        '-R', '--regular-count-only',
        action='store_true',
        dest='regular_count_only',
        default=False,
        help='Perform only the regular count')
    parser.add_argument(
        '-r', '--output-results',
        action='store_true',
        dest='output_results',
        default=False,
        help='Output results instead of election protocol')
    parser.add_argument(
        '-t', '--test-mode',
        action='store_true',
        dest='test_mode',
        default=False,
        help='Test mode. Use a non random drawing')
    parser.add_argument(
        'electionfile',
        metavar='<filename>',
        type=str,
        help=('the election file (.json for --count and '
              'votes-XYZ.zip for --count-lagacy)'))
    args = parser.parse_args(args)
    try:
        if args.count:
            election = standalone.Election(args.electionfile)
            logger.debug("Adding standalone election: %s", election)
        if args.count_legacy:
            election = EvalgLegacyElection(args.electionfile)
            logger.debug("Adding legacy election: %s", election)
        if args.uitstv:
            result, protocol = uitstv.get_result(election)
            election_protocol_dict = protocol.to_dict()
            if args.protocol_file:
                with io.open(args.protocol_file,
                             'w',
                             encoding='utf-8') as protocol_file:
                    protocol_file.write(protocol.render())
            else:
                print(protocol.render())
            quit()
        if args.count_legacy or args.count:
            counter = Counter(election,
                              election.ballots,
                              alternative_paths=args.alternative_paths,
                              test_mode=args.test_mode,
                              interactive_drawing=args.interactive_drawing,
                              regular_count_only=args.regular_count_only)
            if args.dump:
                print(counter.dumps(), flush=True)
                sys.exit(0)
            election_count_tree = counter.count()
            election_count_tree.print_summary()  # debug
            # print(election_count_tree.default_path.get_result().to_json())
            # print(election_count_tree.default_path.get_protocol().to_json())
            if args.output_results:
                results_list = ElectionCountTree.order_results_by(
                    election_count_tree.get_results(),
                    'probability')
                if not results_list:
                    logger.warning(
                        'Results not implemented for election-type: %s',
                        election.type_str)
                    sys.exit(0)
                print('Election tree: {paths} paths total'.format(paths=len(
                    election_count_tree.election_paths)))
                for result_dict in results_list:
                    print('Paths {paths}, probability {prob}'.format(
                        paths=result_dict['paths'],
                        prob=result_dict['probability']))
                    print('Regular candidates:')
                    for cand in result_dict['regulars']:
                        print(cand)
                    if not result_dict['substitutes']:
                        print(os.linesep)
                        continue
                    print('Substitute candidates:')
                    for cand in result_dict['substitutes']:
                        print(cand)
                    print(os.linesep)
            else:
                path_protocol = election_count_tree.default_path.get_protocol()
                if path_protocol is None:
                    logger.warning(
                        'Protocol not implemented for election-type: %s',
                        election.type_str)
                    sys.exit(0)
                if args.protocol_file:
                    with io.open(args.protocol_file,
                                 'w',
                                 encoding='utf-8') as protocol_file:
                        protocol_file.write(path_protocol.render())
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


if __name__ == '__main__':
    logging.basicConfig(level=DEFAULT_LOG_LEVEL, format=DEFAULT_LOG_FORMAT)
    main()
