"""Tests for the census file parsers."""

import io

from werkzeug.test import EnvironBuilder

import evalg.file_parser.parser as cparser


def test_plain_text_usernames():
    """Plain text file, one username per line."""
    usernames = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames)
    assert sorted(result) == sorted(usernames)


def test_plain_text_crlf_usernames():
    """Plain text file, one username per line."""
    usernames = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\r\n'.join(usernames).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames)
    assert sorted(result) == sorted(usernames)


def test_plain_text_fnrs():
    """Plain text file, one fnr per line."""
    fnrs = ['01028512332', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnrs).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'nin'
    result = [x for x in parser.parse()]
    assert len(result) == len(fnrs)
    assert sorted(result) == sorted(fnrs)


def test_plain_text_fnrs_padding():
    """
    Plain text file, one fnr per line.

    Test leftpadding with zero if len(fnr) == 10
    """
    fnrs = ['1028512332', '11235612345', '10100312345']
    fnrs_res = ['01028512332', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnrs).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'nin'
    result = [x for x in parser.parse()]
    assert len(result) == len(fnrs_res)
    assert sorted(result) == sorted(fnrs_res)


def test_plain_text_fnrs_to_short():
    """
    Plain text file, one fnr per line.

    Parser should fail if there are fnr with len(fnr) > 10
    """
    fnrs = ['028512332', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnrs).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is None


def test_plain_text_only_feide_ids():
    """Plain text file, one feide id per line."""
    feide_ids = ['pederaas@uio.no', 'martekir@uio.no',
                 'larsh@uio.no', 'hansta@uio.no']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(feide_ids).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = [x for x in parser.parse()]
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_plain_text_id_missmatch():
    """
    Plain text file, on id per line.

    Parser should fail if there are more then one id type in the file.
    """
    fnr_username = ['pederaas', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnr_username).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])
    assert parser is None

    fnr_feide = ['pederaas@uio.no', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnr_feide).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])
    assert parser is None

    feide_username = ['pederaas@uio.no', 'martekir', 'larsh']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(feide_username).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])
    assert parser is None


def test_plain_text_non_posix_usernames():
    """
    Plain text file, one fnr per line.

    Parser should fail there are space in a username
    """
    usernames = ['pederaas', 'martekir some string', 'larsh', '334', '334%$#', 'example@example.org']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is None


def test_csv_fs_usernames_no_header():
    """Csv file, one username per line."""
    usernames = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.csv')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.CvsParser)
    assert not parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames)
    assert sorted(result) == sorted(usernames)


def test_csv_crlf_fs_usernames_no_header():
    """Csv file, one username per line."""
    usernames = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\r\n'.join(usernames).encode('utf-8')),
                 'usernames.csv')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.CvsParser)
    assert not parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames)
    assert sorted(result) == sorted(usernames)


def test_csv_fs_usernames_with_header():
    """Csv file with header, one username per line."""
    usernames = ['FS.PERSON.BRUKERNAVN',
                 'pederaas', 'martekir', 'larsh', 'hansta']
    usernames_res = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.csv')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.CvsParser)
    assert parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames_res)
    assert sorted(result) == sorted(usernames_res)


def test_csv_fs_usernames_with_header_as_text():
    """If the simple FS csv is save as a txt."""
    usernames = ['FS.PERSON.BRUKERNAVN',
                 'pederaas', 'martekir', 'larsh', 'hansta']
    usernames_res = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames_res)
    assert sorted(result) == sorted(usernames_res)


def test_csv_fs_student_parlament_file():
    """
    Csv file for the student parlament election.

    With header, two columns. username, faculty nr
    """
    usernames = ["FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
                 'pederaas, 15',
                 'martekir, 12',
                 'larsh, 12',
                 'hansta, 15']
    usernames_res = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.csv')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.CvsParser)
    assert parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames_res)
    assert sorted(result) == sorted(usernames_res)


def test_csv_fs_student_parlament_file_missing_field():
    """
    Csv file for the student parlament election.

    With header, two columns. username, faculty nr
    """
    usernames = ["FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
                 'pederaas, 15',
                 'martekir, 12',
                 'larsh',
                 'hansta,']
    usernames_res = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.csv')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.CvsParser)
    assert parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames_res)
    assert sorted(result) == sorted(usernames_res)


def test_csv_fs_student_parlament_file_as_txt():
    """
    Csv for the student parlament election, uploaded as a txt file.

    With header, two columns. username, faculty nr
    """
    usernames = ["FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
                 'pederaas, 15',
                 'martekir, 12',
                 'larsh, 12',
                 'hansta, 15']
    usernames_res = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.txt')})
    parser = cparser.CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.has_fs_header
    assert parser.id_type == 'uid'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames_res)
    assert sorted(result) == sorted(usernames_res)
