#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = 'pdorclient',
    version = '0.4.4',
    author = 'Saj Goonatilleke',
    author_email = 'sg@redu.cx',

    description = 'PowerDNS on Rails client library',
    long_description = """
Use pdorclient to read and manipulate PowerDNS zone and record data from
your Python applications.  This client-side library was designed to
work with the RESTful API exposed by PowerDNS on Rails.
    """,
    license = 'BSD',
    platforms = [ 'Linux', 'Unix' ],

    classifiers = [
      'Development Status :: 4 - Beta',
      'Intended Audience :: System Administrators',
      'License :: OSI Approved :: BSD License',
      'Operating System :: POSIX',
      'Programming Language :: Python',
      'Topic :: Internet :: Name Service (DNS)',
      'Topic :: System :: Systems Administration',
    ],

    install_requires = [
      'httplib2',
      'lxml',
      'restclient',
      'simplejson',
    ],

    packages = find_packages(exclude=['tests']),
)
