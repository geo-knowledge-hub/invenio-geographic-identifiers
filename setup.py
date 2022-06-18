# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers vocabulary for the InvenioRDM"""

import os

from setuptools import find_packages, setup

readme = open("README.rst").read()
history = open("CHANGES.rst").read()

invenio_db_version = ">=1.0.14,<2.0.0"
invenio_search_version = ">=1.4.2,<2.0"

tests_require = [
    "pytest-mock>=1.6.0",
    "pytest-invenio>=1.4.0",
    "invenio-app>=1.3.1,<2.0.0",
]

extras_require = {
    "docs": [
        "sphinx>=4.2.0,<5",
    ],
    "tests": tests_require,
    # Elasticsearch
    "elasticsearch7": [
        f"invenio-search[elasticsearch7]{invenio_search_version}",
    ],
    # Databases
    "mysql": [
        f"invenio-db[mysql,versioning]{invenio_db_version}",
    ],
    "postgresql": [
        f"invenio-db[postgresql,versioning]{invenio_db_version}",
    ],
    "sqlite": [
        f"invenio-db[versioning]{invenio_db_version}",
    ],
}
extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup_requires = [
    'Babel>=2.8',
]

install_requires = [
    "invenio-i18n>=1.2.0",
    "invenio-vocabularies>=0.11.5"
]

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('invenio_geographic_identifiers', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='invenio-geographic-identifiers',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio TODO',
    license='MIT',
    author='GEO Secretariat',
    author_email='secretariat@geosec.org',
    url='https://github.com/geo-knowledge-hub/invenio-geographic-identifiers',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'flask.commands': [
            'geoidentifiers = invenio_geographic_identifiers.cli:geoidentifiers'
        ],
        'invenio_base.apps': [
            'geoidentifiers = invenio_geographic_identifiers:InvenioGeographicIdentifiers',
        ],
        "invenio_base.api_apps": [
            "geoidentifiers = invenio_geographic_identifiers:InvenioGeographicIdentifiers",
        ],
        "invenio_base.blueprints": [
            "geoidentifiers = invenio_geographic_identifiers.views:blueprint"
        ],
        "invenio_base.api_blueprints": [
            "geoidentifiers = invenio_geographic_identifiers.views:create_geoidentifiers_blueprint_from_app"
        ],
        "invenio_db.models": [
            "geoidentifiers = invenio_geographic_identifiers.geoidentifiers.models"
        ],
        "invenio_jsonschemas.schemas": [
            "geoidentifiers = invenio_geographic_identifiers.geoidentifiers.jsonschemas"
        ],
        "invenio_search.mappings": [
            "geoidentifiers = invenio_geographic_identifiers.geoidentifiers.mappings"
        ],
        # 'invenio_access.actions': [],
        # 'invenio_admin.actions': [],
        # 'invenio_assets.bundles': [],
        # 'invenio_base.api_apps': [],
        # 'invenio_base.api_blueprints': [],
        # 'invenio_base.blueprints': [],
        # 'invenio_celery.tasks': [],
        # 'invenio_db.models': [],
        # 'invenio_pidstore.minters': [],
        # 'invenio_records.jsonresolver': [],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Development Status :: 1 - Planning',
    ],
)
