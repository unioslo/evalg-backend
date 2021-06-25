import io
import pytest

from werkzeug.test import EnvironBuilder


@pytest.fixture
def uids():
    """A list of uids."""
    return ['pederaas', 'martekir', 'larsh', 'hansta']


@pytest.fixture
def uids_upper_case():
    """A list of uids."""
    return ['PEDERAAS', 'MARTEKIR', 'LARSH', 'HANSTA']


@pytest.fixture
def uids_empty_line_end():
    """A list of uids."""
    return ['pederaas', 'martekir', 'larsh', 'hansta', '', '']


@pytest.fixture
def uids_empty_line_middle():
    """A list of uids."""
    return ['pederaas', 'martekir', '', 'larsh', 'hansta']


@pytest.fixture
def uids_empty_line_start():
    """A list of uids."""
    return ['', 'pederaas', 'martekir', 'larsh', 'hansta']


@pytest.fixture
def uids_empty_line_mix():
    """A list of uids."""
    return ['', 'pederaas', 'martekir', '', 'larsh', 'hansta', '']


@pytest.fixture
def uids_whitespace_lines():
    """A list of uids."""
    return ['  ', 'pederaas', 'martekir', '\t', 'larsh', 'hansta', '\t  ']


@pytest.fixture
def uids_mixed_case():
    """A list of uids."""
    return ['PEDERAAS', 'martekir', 'larsh', 'HANSTA']


@pytest.fixture()
def uids_fs():
    """A list of uids with a FS header as the first element."""
    return ['FS.PERSON.BRUKERNAVN', 'pederaas', 'martekir', 'larsh', 'hansta']


@pytest.fixture
def uids_student_parliament():
    """Lines of a student parliament census file."""
    return [
        "FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
        'pederaas, 15',
        'martekir, 12',
        'larsh, 12',
        'hansta, 15']


@pytest.fixture
def uids_student_parliament_missing_faknr():
    """Lines of a student parliament census file, whith missing fields."""
    return [
        "FS.PERSON.BRUKERNAVN||','||FS.STUDIEPROGRAM.FAKNR_STUDIEANSV",
        'pederaas, 15',
        'martekir, 12',
        'larsh',
        'hansta,']


@pytest.fixture
def uids_non_posix():
    """A list of uids, where some do not conform to POSIX."""
    return ['pederaas',
            'martekir some string',
            'larsh',
            '334',
            '334%$#',
            'example@example.org']


@pytest.fixture
def feide_ids(uids):
    """A list of feide ids."""
    return ['{}@uio.no'.format(x) for x in uids]


@pytest.fixture
def nins():
    """A list of norwegian national ids."""
    return ['01028512332', '11235612345', '10100312345']


@pytest.fixture
def nins_10(nins):
    """A list of norwegian national ids, where the leading zero is removed."""
    return [x[1:] if x[0] == '0' else x for x in nins]


@pytest.fixture
def nins_error(nins):
    """A list of norwegian national ids, with errors."""
    nins[0] = nins[0][3:]
    return nins


@pytest.fixture
def ids_mix_1():
    """A list of mixed ids (uid and nin)."""
    return ['pederaas', '11235612345', '10100312345']


@pytest.fixture
def ids_mix_2():
    """A list of mixed ids (feide_id and nin)."""
    return ['pederaas@uio.no', '11235612345', '10100312345']


@pytest.fixture
def ids_mix_3():
    """A list of mixed ids (feide_id and uid)."""
    return ['pederaas@uio.no', 'martekir', 'larsh']


def generate_census_file_builder(ids, file_ending, linebrake='\n'):
    """Generate census test files."""
    return EnvironBuilder(method='POST', data={
        'file': (io.BytesIO(linebrake.join(ids).encode('utf-8')),
                 'usernames.{}'.format(file_ending))})


@pytest.fixture
def uid_plane_text_census_builder(feide_ids):
    """Plain text census file of feide ids."""
    return generate_census_file_builder(feide_ids, 'txt')


@pytest.fixture
def uid_plane_text_crlf_census_builder(feide_ids):
    """Plain text census file of feide ids."""
    return generate_census_file_builder(feide_ids, 'txt', linebrake='\r\n')


@pytest.fixture
def uids_plane_text_empty_line_end_census_builder(uids_empty_line_end):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_end, 'txt')


@pytest.fixture
def uids_plane_text_empty_line_middle_census_builder(uids_empty_line_middle):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_middle, 'txt')


@pytest.fixture
def uids_plane_text_empty_line_start_census_builder(uids_empty_line_start):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_start, 'txt')


@pytest.fixture
def uids_plane_text_empty_line_mix_census_builder(uids_empty_line_mix):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_mix, 'txt')


@pytest.fixture
def uids_plane_text_whitespace_lines_census_builder(uids_whitespace_lines):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_whitespace_lines, 'txt')


@pytest.fixture
def uids_csv_empty_line_end_census_builder(uids_empty_line_end):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_end, 'csv')


@pytest.fixture
def uids_csv_empty_line_middle_census_builder(uids_empty_line_middle):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_middle, 'csv')


@pytest.fixture
def uids_csv_empty_line_start_census_builder(uids_empty_line_start):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_start, 'csv')


@pytest.fixture
def uids_csv_empty_line_mix_census_builder(uids_empty_line_mix):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_empty_line_mix, 'csv')


@pytest.fixture
def uids_csv_whitespace_lines_census_builder(uids_whitespace_lines):
    """Plane text census file with empty lines."""
    return generate_census_file_builder(uids_whitespace_lines, 'csv')


@pytest.fixture
def uid_plane_text_upper_case_builder(uids_upper_case):
    """Plain text upper case census file."""
    return generate_census_file_builder(uids_upper_case, 'txt')


@pytest.fixture
def uid_plane_text_mixed_case_builder(uids_mixed_case):
    """Plain text upper case census file."""
    return generate_census_file_builder(uids_mixed_case, 'txt')


@pytest.fixture
def uid_csv_census_builder(feide_ids):
    """Plain text census file of feide ids."""
    return generate_census_file_builder(feide_ids, 'csv')


@pytest.fixture
def feide_id_plane_text_census_builder(feide_ids):
    """Plain text census file of feide ids."""
    return generate_census_file_builder(feide_ids, 'txt')


@pytest.fixture
def feide_id_cvs_census_builder(feide_ids):
    """Plain text census file of feide ids."""
    return generate_census_file_builder(feide_ids, 'csv')


@pytest.fixture
def nin_plane_text_census_builder(nins):
    """Plain text census file of nins."""
    return generate_census_file_builder(nins, 'txt')


@pytest.fixture
def nin_csv_census_builder(nins):
    """Plain text census file of nins."""
    return generate_census_file_builder(nins, 'csv')


@pytest.fixture
def nin_10_plane_text_census_builder(nins_10):
    """Plain text census file of nins, where leading 0 is removed."""
    return generate_census_file_builder(nins_10, 'txt')


@pytest.fixture
def nin_error_plane_text_census_builder(nins_error):
    """Plain text census file of nins, with errors."""
    return generate_census_file_builder(nins_error, 'txt')


@pytest.fixture
def uid_student_parliament_builder(uids_student_parliament):
    """Csv census file of of uids from FS."""
    return generate_census_file_builder(uids_student_parliament, 'csv')


@pytest.fixture
def uid_student_parliament_missing_builder(
        uids_student_parliament_missing_faknr):
    """Csv census file of of uids from FS."""
    return generate_census_file_builder(uids_student_parliament_missing_faknr,
                                        'csv')


@pytest.fixture
def uid_student_parliament_as_txt_builder(uids_student_parliament):
    """Csv census file of of uids from FS."""
    return generate_census_file_builder(uids_student_parliament, 'txt')


@pytest.fixture
def uid_fs_csv_builder(uids_fs):
    """FS census file with header."""
    return generate_census_file_builder(uids_fs, 'csv')


@pytest.fixture
def uid_fs_csv_as_txt_builder(uids_fs):
    """FS census file with header as txt."""
    return generate_census_file_builder(uids_fs, 'txt')


@pytest.fixture
def uid_not_posix_txt_builder(uids_non_posix):
    """Uid plane text file with non posix uids."""
    return generate_census_file_builder(uids_non_posix, 'txt')


@pytest.fixture
def ids_mix_txt_1_builder(ids_mix_1):
    """Census file with a mix of ids."""
    return generate_census_file_builder(ids_mix_1, 'txt')


@pytest.fixture
def ids_mix_txt_2_builder(ids_mix_2):
    """Census file with a mix of ids."""
    return generate_census_file_builder(ids_mix_2, 'txt')


@pytest.fixture
def ids_mix_txt_3_builder(ids_mix_3):
    """Census file with a mix of ids."""
    return generate_census_file_builder(ids_mix_3, 'txt')


@pytest.fixture
def uid_zip_builder(uids):
    """Uids as zip file."""
    return generate_census_file_builder(uids, 'zip')
