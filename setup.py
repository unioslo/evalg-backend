#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup file for eValg."""
from __future__ import print_function

import sys

import pkg_resources
import setuptools
import setuptools.command.test


def get_requirements(filename):
    """Read requirements from file."""
    with open(filename, mode='rt', encoding='utf-8') as f:
        requirements = iter(pkg_resources.parse_requirements(f))
        for requirement in requirements:
            yield str(requirement)


def get_textfile(filename):
    """Get contents from a text file."""
    with open(filename, mode='rt', encoding='utf-8') as f:
        return f.read().lstrip()


def get_packages():
    """List of (sub)packages to install."""
    return setuptools.find_packages('.', include=('evalg', 'evalg.*'))


class PyTest(setuptools.command.test.test):
    """
    Run tests using pytest.

    From `http://doc.pytest.org/en/latest/goodpractices.html`.
    """

    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        super(PyTest, self).initialize_options()
        self.pytest_args = []

    def run_tests(self):
        import shlex
        import pytest
        args = self.pytest_args
        if args:
            args = shlex.split(args)
        errno = pytest.main(args)
        raise SystemExit(errno)


def run_setup():
    """Build and run setup."""

    setup_requirements = ['setuptools_scm']
    test_requirements = list(get_requirements('requirements-test.txt'))
    install_requirements = list(get_requirements('requirements.txt'))

    if {'build_sphinx', 'upload_docs'}.intersection(sys.argv):
        # Sphinx modules:
        setup_requirements.extend(get_requirements('docs/requirements.txt'))
        # pofh-dependencies for generating autodoc:
        # setup_requirements.extend(get_requirements('requirements.txt'))

    setuptools.setup(
        name='evalg',
        description='An electronic voting application',
        long_description=get_textfile('README.md'),
        long_description_content_type='text/markdown',

        url='https://bitbucket.usit.uio.no/projects/EVALG/repos/evalg/',
        author='USIT, University of Oslo',
        author_email='bnt-int@usit.uio.no',

        use_scm_version=True,
        packages=get_packages(),
        package_data={
            'evalg.counting.templates': ['*.tmpl'],
            'evalg.mail.templates': ['*.tmpl'],
        },
        python_requires='~= 3.6',
        setup_requires=setup_requirements,
        install_requires=install_requirements,
        tests_require=test_requirements,
        cmdclass={
            'test': PyTest,
        },
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: Education',
            # TODO/TBD: 'License :: OSI Approved :: MIT License',
            'Topic :: Software Development :: Libraries',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Topic :: System :: Systems Administration',
        ],
        keywords='evalg electronic election',
    )


if __name__ == "__main__":
    run_setup()
