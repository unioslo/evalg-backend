"""Tests for the census file parsers."""

import io
import pytest

from werkzeug.test import EnvironBuilder

import evalg.file_parser.parser as cparser

IDS = {
    'uid': ['pederaas', 'martekir', 'larsh', 'hansta'],
    'uid_fs': ['FS.PERSON.BRUKERNAVN',
               'pederaas',
               'martekir',
               'larsh',
               'hansta'],
    'nin': ['01028512332', '11235612345', '10100312345'],
    # nin with leading zero removed
    'nin_10': ['1028512332', '11235612345', '10100312345'],
    # Invalid norwegian nin
    'nin_error': ['028512332', '11235612345', '10100312345'],
    'feide_ids': ['pederaas@uio.no',
                  'martekir@uio.no',
                  'larsh@uio.no',
                  'hansta@uio.no'],
    'mix_1': ['pederaas', '11235612345', '10100312345'],
    'mix_2': ['pederaas@uio.no', '11235612345', '10100312345'],
    'mix_3': ['pederaas@uio.no', 'martekir', 'larsh'],
    'uid_non_posix': ['pederaas',
                      'martekir some string',
                      'larsh',
                      '334',
                      '334%$#',
                      'example@example.org'],
    'student_parliament': [
        "FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
        'pederaas, 15',
        'martekir, 12',
        'larsh, 12',
        'hansta, 15'],
    'student_parliament_missing': [
        "FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
        'pederaas, 15',
        'martekir, 12',
        'larsh',
        'hansta,'],
}


def create_builder(ids, crlf=False, file_type='txt'):
    """Create EnvironBuilder to simulate files."""
    if crlf:
        line_break = '\r\n'
    else:
        line_break = '\n'
    return EnvironBuilder(method='POST', data={
        'file': (io.BytesIO(line_break.join(ids).encode('utf-8')),
                 'pollbook.{}'.format(file_type))})


@pytest.mark.parametrize(
    "builder,expected_results,expected_id_type,expected_parser",
    [
        (create_builder(IDS['uid']),
         ['{0}@uio.no'.format(x) for x in IDS['uid']],
         'feide_id',
         cparser.PlainTextParser),
        (create_builder(IDS['uid'], crlf=True),
         ['{0}@uio.no'.format(x) for x in IDS['uid']],
         'feide_id',
         cparser.PlainTextParser),
        (create_builder(IDS['nin']),
         IDS['nin'],
         'nin',
         cparser.PlainTextParser),
        # Check padding
        (create_builder(IDS['nin_10']),
         IDS['nin'],
         'nin',
         cparser.PlainTextParser),
        # Nin with errors
        (create_builder(IDS['nin_error']), None, None, None),
        (create_builder(IDS['feide_ids']),
         IDS['feide_ids'],
         'feide_id',
         cparser.PlainTextParser),
        # Invalid file type
        (create_builder(IDS['uid'], file_type='zip'), None, None, None),
        (create_builder(IDS['mix_1']), None, None, None),
        (create_builder(IDS['mix_2']), None, None, None),
        (create_builder(IDS['mix_3']), None, None, None),
        (create_builder(IDS['uid_non_posix']), None, None, None),
        (create_builder(IDS['uid'], file_type='csv'),
         IDS['feide_ids'],
         'feide_id',
         cparser.CsvParser),
        # CSV file without headers
        (create_builder(IDS['uid'], crlf=True, file_type='csv'),
         IDS['feide_ids'],
         'feide_id',
         cparser.CsvParser),
        # CVS file with FS headers
        (create_builder(IDS['uid_fs'], file_type='csv'),
         IDS['feide_ids'],
         'feide_id',
         cparser.CsvParser),
        # FS csv file with header as a txt file
        (create_builder(IDS['uid_fs'], file_type='txt'),
         IDS['feide_ids'],
         'feide_id',
         cparser.PlainTextParser),
        # Student parliament file
        (create_builder(IDS['student_parliament'], file_type='csv'),
         IDS['feide_ids'],
         'feide_id',
         cparser.CsvParser),
        # Student parliament file with missing fields
        (create_builder(IDS['student_parliament_missing'], file_type='csv'),
         IDS['feide_ids'],
         'feide_id',
         cparser.CsvParser),
        # Student parliament csv file as a txt file.
        (create_builder(IDS['student_parliament'], file_type='txt'),
         IDS['feide_ids'],
         'feide_id',
         cparser.PlainTextParser),
        ]
)
def test_plain_text_parser(builder,
                           expected_results,
                           expected_id_type,
                           expected_parser):
    """Plain text file, one username per line."""
    if expected_results:
        parser = cparser.CensusFileParser.factory(builder.files['file'])
        assert parser is not None
        assert isinstance(parser, expected_parser)
        assert parser.id_type == expected_id_type
        result = list(parser.parse())
        assert len(result) == len(expected_results)
        assert sorted(result) == sorted(expected_results)
    else:
        with pytest.raises(ValueError):
            cparser.CensusFileParser.factory(builder.files['file'])
