..
    Copyright (C) 2022 GEO Secretariat.

    invenio-geographic-identifiers is free software; you can redistribute
    it and/or modify it under the terms of the MIT License; see LICENSE file
    for more details.

================================
 Invenio-Geographic-Identifiers
================================

.. image:: https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/workflows/CI/badge.svg
        :target: https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/actions?query=workflow%3ACI

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/lifecycle-maturing-blue.svg
        :target: https://www.tidyverse.org/lifecycle/#maturing
        :alt: Software Life Cycle

.. image:: https://img.shields.io/github/license/geo-knowledge-hub/invenio-geographic-identifiers.svg
        :target: https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/blob/master/LICENSE

.. image:: https://img.shields.io/github/tag/geo-knowledge-hub/invenio-geographic-identifiers.svg
        :target: https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/releases

.. image:: https://img.shields.io/discord/730739436551143514?logo=discord&logoColor=ffffff&color=7389D8
        :target: https://discord.com/channels/730739436551143514#
        :alt: Join us at Discord

Geographic identifiers vocabularies for the InvenioRDM.

Development
===========

Install
-------

Choose a version of `elasticsearch` and a `DB`, then run:

.. code-block:: console

    pip install -e .[elasticsearch7]
    pip install invenio-db[<[mysql|postgresql|]>,versioning]


Tests
-----

.. code-block:: console

    pipenv run ./run-tests.sh
