"""Pollbook file parser."""
import abc
import csv
import io
import re


class CensusFileParser(metaclass=abc.ABCMeta):
    """Abstract parser class."""

    def __init__(self, census_file, feide_postfix='uio.no'):
        self.census_file = census_file
        self._id_type = None
        self._convert_to_feide = False
        self.fields = None
        self.feide_postfix = feide_postfix

    def parse(self):
        """Parse the current file and create a generator."""
        if not self.id_type:
            return

        if self.id_type == 'nin':
            for fnr in self.fields:
                fnr = self.check_and_rjust_fnr(fnr)
                if fnr:
                    yield fnr
                else:
                    continue
        elif self.id_type == 'feide_id':
            for field in self.fields:

                # Remove whitespaces
                field = field.strip()
                if len(field) == 0:
                    continue

                if self._convert_to_feide:
                    yield "{}@{}".format(field.lower(), self.feide_postfix)
                else:
                    yield field.lower()
        else:
            return

    @classmethod
    @abc.abstractmethod
    def get_mime_types(cls):
        """Get the mimetype supported by the parser."""

    @property
    def id_type(self):
        """Get the id type returned by the generator."""
        return self._id_type

    @id_type.setter
    def id_type(self, id_type):
        """
        Set the id type.

        UIDs are converted to feide_ids.
        """
        if id_type == 'uid':
            # Covert uids to feide
            self._convert_to_feide = True
            self._id_type = 'feide_id'
        else:
            self._id_type = id_type

    @classmethod
    def find_identifier_type(cls, ids):
        """
        Find the identity type of a list of identities.

        All of the identifiers needs to be of the same type.
        """
        if not ids:
            raise ValueError('No ids given')

        # Remove empty lines or lines with only whitespaces
        ids = [x.strip() for x in ids if len(x.strip()) > 0]
        try:
            [int(x) for x in ids]
        except ValueError:
            pass
        else:
            if len({s for s in [len(x) for x in ids]} -
                   {s for s in [10, 11]}) == 0:
                return 'nin'
            raise ValueError('File contains invalid NINs')

        if all(['@' in x for x in ids]):
            if all([cls.is_posix_uid(x.split('@')[0]) for x in ids]):
                return 'feide_id'

            raise ValueError('File contains invalid Feide IDs')

        if any(['@' in x for x in ids]):
            # Probably a feide id or email mixed in with usernames
            raise ValueError('Invalid ids, mix of feide and other ids')

        if all([cls.is_posix_uid(x) for x in ids]):
            return 'uid'

        if all([cls.is_posix_uid(x.lower()) for x in ids]):
            return 'uid'

        raise ValueError('No supported id type found in file')

    @classmethod
    def check_and_rjust_fnr(cls, fnr):
        """
        Preform some rudimentary checks on a fnr.

        If the len is 10 we assume that a leading zero is missing.
        TODO: Validate the fnrs
        """
        try:
            int(fnr)
        except ValueError:
            return None

        if len(fnr) == 10:
            # Probably missing a leading zero.
            fnr = fnr.rjust(11, '0')
        elif len(fnr) < 10:
            # Invalid fnr
            return None

        return fnr

    @classmethod
    def is_posix_uid(cls, uid):
        """Test if uid is a valid posix uid."""
        valid_posix_uid = '^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\\$)$'
        res = re.search(valid_posix_uid, uid)
        return bool(res)

    @classmethod
    def is_fs_header(cls, header):
        """Check if a string matches a FS header."""
        if header.startswith('FS.PERSON.BRUKERNAVN'):
            return True

    @classmethod
    def get_supported_mime_types(cls):
        """Get the mime types of all implemented subclasses."""
        supported_mime_typs = []
        return (supported_mime_typs.extend(x.get_mime_types()) for x in
                CensusFileParser.__subclasses__())

    @classmethod
    def factory(cls, census_file, mime_type, feide_postfix='uio.no'):
        """Return the correct file parser if supported."""

        supported_mime_types = {}

        for parser in CensusFileParser.__subclasses__():
            for mt in parser.get_mime_types():
                if mt in supported_mime_types:
                    raise ValueError('Multiple parsers defiend for MIME type')
                supported_mime_types[mt] = parser

        if mime_type in supported_mime_types:
            parser = supported_mime_types[mime_type](
                census_file, feide_postfix=feide_postfix)

            if parser.id_type is None:
                # No supported id type in file
                raise ValueError(
                    'Content in file not valid for file type {}'.format(
                        census_file.mimetype
                    ))
            return parser
        raise ValueError('No parser for filetype {}'.format(
            mime_type))


class PlainTextParser(CensusFileParser):
    """A parser for plain text file files."""

    def __init__(self, census_file, feide_postfix):
        super().__init__(census_file, feide_postfix)
        content = self.census_file.decode('utf-8')
        self.fields = content.splitlines()

        if len(self.fields) > 0 and self.is_fs_header(self.fields[0]):
            # TODO: Remove this..?
            # File is a csv file erroneously save as .txt.
            parser = CsvParser(self.census_file, feide_postfix=feide_postfix)
            self.fields = [x for x in parser.parse()]
            self.has_fs_header = True
        else:
            self.has_fs_header = False
        self.id_type = self.find_identifier_type(self.fields)

    @classmethod
    def get_mime_types(cls):
        """File mime type."""
        return ['text/plain']


class CsvParser(CensusFileParser):
    """A parser for CSV files."""

    def __init__(self, census_file, feide_postfix):
        super().__init__(census_file, feide_postfix)
        csvfile = io.StringIO(self.census_file.decode('utf-8'))

        first_line = csvfile.readline()
        self.has_fs_header = self.is_fs_header(first_line)
        if not self.has_fs_header:
            # No fs header, move back to file start
            csvfile.seek(0)

        self.fields = [x[0] for x in csv.reader(csvfile) if x and x[0]]
        self.id_type = self.find_identifier_type(self.fields)

    @classmethod
    def get_mime_types(cls):
        """File mime type."""
        return [
            'text/x-csv',
            'application/vnd.ms-excel',
            'application/csv',
            'application/x-csv',
            'text/csv',
            'text/comma-separated-values',
            'text/x-comma-separated-values',
            'text/tab-separated-values',
            ]
