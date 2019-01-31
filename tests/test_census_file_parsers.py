"""Tests for the census file parsers."""

import io

from werkzeug.test import EnvironBuilder

from evalg.file_parser.parser import CensusFileParser


def test_plain_text_usernames():
    """Plain text file, one username per line."""
    usernames = ['pederaas', 'martekir', 'larsh', 'hansta']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')),
                 'usernames.txt')})
    parser = CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert parser.id_type == 'username'
    result = [x for x in parser.parse()]
    assert len(result) == len(usernames)
    assert sorted(result) == sorted(usernames)


def test_plain_text_fnrs():
    """Plain text file, one fnr per line."""
    fnrs = ['01028512332', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnrs).encode('utf-8')),
                 'usernames.txt')})
    parser = CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert parser.id_type == 'fnr'
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
    parser = CensusFileParser.factory(builder.files['file'])

    assert parser is not None
    assert parser.id_type == 'fnr'
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
    parser = CensusFileParser.factory(builder.files['file'])

    assert parser is None


def test_plain_text_only_feide_ids():
    """Plain text file, one feide id per line."""
    feide_ids = ['pederaas@uio.no', 'martekir@uio.no',
                 'larsh@uio.no', 'hansta@uio.no']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(feide_ids).encode('utf-8')),
                 'usernames.txt')})
    parser = CensusFileParser.factory(builder.files['file'])

    assert parser is not None
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
    parser = CensusFileParser.factory(builder.files['file'])
    assert parser is None

    fnr_feide = ['pederaas@uio.no', '11235612345', '10100312345']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(fnr_feide).encode('utf-8')),
                 'usernames.txt')})
    parser = CensusFileParser.factory(builder.files['file'])
    assert parser is None

    feide_username = ['pederaas@uio.no', 'martekir', 'larsh']
    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(feide_username).encode('utf-8')),
                 'usernames.txt')})
    parser = CensusFileParser.factory(builder.files['file'])
    assert parser is None


def test_plain_text_space_in_usernames():
    """
    Plain text file, one fnr per line.

    Parser should fail there are space in a username
    """
    usernames = ['pederaas', 'martekir some string', 'larsh']

    builder = EnvironBuilder(method='POST', data={
        'file': (io.BytesIO('\n'.join(usernames).encode('utf-8')), 'usernames.txt')})

    parser = CensusFileParser.factory(builder.files['file'])
    assert parser is None
