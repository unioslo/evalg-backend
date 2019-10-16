"""Tests for the census file parsers."""

import pytest

import evalg.file_parser.parser as cparser


def test_uid_plain_text(uid_plane_text_census_builder, feide_ids):
    """Test parsing of plain text uid file."""
    file = uid_plane_text_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_uid_plain_text_crlf(uid_plane_text_crlf_census_builder, feide_ids):
    """Test parsing of plain text uid file, with crlf linebrakes."""
    census_file = uid_plane_text_crlf_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(census_file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_uid_plain_text_upper_case(uid_plane_text_upper_case_builder,
                                   feide_ids):
    """Test parsing of plain text uid file, with crlf linebrakes."""
    census_file = uid_plane_text_upper_case_builder.files['file']
    parser = cparser.CensusFileParser.factory(census_file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_uid_plain_text_mixed_case(uid_plane_text_mixed_case_builder,
                                   feide_ids):
    """Test parsing of plain text uid file, with crlf linebrakes."""
    census_file = uid_plane_text_mixed_case_builder.files['file']
    parser = cparser.CensusFileParser.factory(census_file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_uid_cvs(uid_csv_census_builder, feide_ids):
    """Test parsing of csv uid file."""
    file = uid_csv_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.CsvParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_feide_id_plane_text(feide_id_plane_text_census_builder, feide_ids):
    """Test parsing of plane text file with feide ids."""
    file = feide_id_plane_text_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_feide_id_csv(feide_id_cvs_census_builder, feide_ids):
    """Test parsing of csv file with feide ids."""
    file = feide_id_cvs_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.CsvParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_nin_plane_text(nin_plane_text_census_builder, nins):
    """Test parsing of plane text file with nins."""
    file = nin_plane_text_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'nin'
    result = list(parser.parse())
    assert len(result) == len(nins)
    assert sorted(result) == sorted(nins)


def test_nin_csv_file(nin_csv_census_builder, nins):
    """Test parsing of csv file with nins."""
    file = nin_csv_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.CsvParser)
    assert parser.id_type == 'nin'
    result = list(parser.parse())
    assert len(result) == len(nins)
    assert sorted(result) == sorted(nins)


def test_nin_10_plane_text(nin_10_plane_text_census_builder, nins):
    """Test parsing of nins with missing leading zero."""
    file = nin_10_plane_text_census_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'nin'
    result = list(parser.parse())
    assert len(result) == len(nins)
    assert sorted(result) == sorted(nins)


def test_nin_error(nin_error_plane_text_census_builder):
    """Test parsing of nins with error."""
    file = nin_error_plane_text_census_builder.files['file']
    with pytest.raises(ValueError):
        cparser.CensusFileParser.factory(file)


def test_student_parliament_file(uid_student_parliament_builder, feide_ids):
    """Test parsing of student parliament file."""
    file = uid_student_parliament_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.CsvParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_student_parliament_file_missing(
        uid_student_parliament_missing_builder, feide_ids):
    """Test parsing of student parliament with missing fields."""
    file = uid_student_parliament_missing_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.CsvParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_student_parliament_file_as_txt(
        uid_student_parliament_as_txt_builder, feide_ids):
    """Test parsing of student parliament file as txt."""
    file = uid_student_parliament_as_txt_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_fs_csv(uid_fs_csv_builder, feide_ids):
    """Test parsing of FS file."""
    file = uid_fs_csv_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.CsvParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_fs_as_txt(uid_fs_csv_as_txt_builder, feide_ids):
    """Test parsing of FS file as txt."""
    file = uid_fs_csv_as_txt_builder.files['file']
    parser = cparser.CensusFileParser.factory(file)
    assert parser is not None
    assert isinstance(parser, cparser.PlainTextParser)
    assert parser.id_type == 'feide_id'
    result = list(parser.parse())
    assert len(result) == len(feide_ids)
    assert sorted(result) == sorted(feide_ids)


def test_not_supported_file_type(uid_zip_builder):
    """Test unsupported file type."""
    file = uid_zip_builder.files['file']
    with pytest.raises(ValueError):
        cparser.CensusFileParser.factory(file)


def test_ids_mix_1(ids_mix_txt_1_builder):
    """Test mix of id types, variant 1."""
    file = ids_mix_txt_1_builder.files['file']
    with pytest.raises(ValueError):
        cparser.CensusFileParser.factory(file)


def test_ids_mix_2(ids_mix_txt_2_builder):
    """Test mix of id types, variant 2."""
    file = ids_mix_txt_2_builder.files['file']
    with pytest.raises(ValueError):
        cparser.CensusFileParser.factory(file)


def test_ids_mix_3(ids_mix_txt_3_builder):
    """Test mix of id types, variant 3."""
    file = ids_mix_txt_3_builder.files['file']
    with pytest.raises(ValueError):
        cparser.CensusFileParser.factory(file)


def test_uid_non_posix(uid_not_posix_txt_builder):
    """Test parsing of non posix uids."""
    file = uid_not_posix_txt_builder.files['file']
    with pytest.raises(ValueError):
        cparser.CensusFileParser.factory(file)
