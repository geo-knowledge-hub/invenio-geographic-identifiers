# Invenio Geographic Identifiers

[![CI](https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/workflows/CI/badge.svg)](https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/actions?query=workflow%3ACI)
[![License](https://img.shields.io/github/license/geo-knowledge-hub/invenio-geographic-identifiers.svg)](https://github.com/geo-knowledge-hub/invenio-geographic-identifiers/blob/master/LICENSE)

Geographic identifier vocabularies for InvenioRDM instances.

## About

`Invenio Geographic Identifiers` is a Python library that adds a `geoidentifiers` vocabulary to an InvenioRDM instance.

Identifiers are loaded through the [Invenio Vocabularies](https://github.com/inveniosoftware/invenio-vocabularies) datastreams API, which reads a source, transforms each entry and writes it to the vocabulary. [GeoNames](https://www.geonames.org/) is supported out of the box. Other schemes can be added by writing a transformer.

The package supports InvenioRDM v13 on Python 3.9, 3.11 and 3.12, and requires OpenSearch 2.12 or newer.

## Getting started

To start, you first need to install the Python distribution in your instance. For this, you can use your favorite package manager. Assuming you are using the default pipenv from InvenioRDM, you can add the package to the `Pipfile` of your instance as follows:

> Currently, the package is only available on GitHub, but soon it will be available on PyPI.org as well.

```toml
[packages]
invenio-geographic-identifiers = {git = "https://github.com/geo-knowledge-hub/invenio-geographic-identifiers.git"}
```

The vocabulary, its REST resource, its search mapping and its database tables are all registered automatically. The one thing an instance has to declare is where the datastreams come from, because the readers, transformers and writers are resolved by name from the application configuration. For this, in your `invenio.cfg` you can include the values defined by the package:

```python
from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    VOCABULARIES_DATASTREAM_READERS as GEONAMES_READERS,
    VOCABULARIES_DATASTREAM_TRANSFORMERS as GEONAMES_TRANSFORMERS,
    VOCABULARIES_DATASTREAM_WRITERS as GEONAMES_WRITERS,
)

VOCABULARIES_DATASTREAM_READERS = {**GEONAMES_READERS}
VOCABULARIES_DATASTREAM_TRANSFORMERS = {**GEONAMES_TRANSFORMERS}
VOCABULARIES_DATASTREAM_WRITERS = {**GEONAMES_WRITERS}
```

Then install the package and create the tables and the search index:

```shell
invenio-cli install
invenio-cli services setup
```

## Loading a vocabulary

To load a vocabulary into your instance, you first need to have the `allCountries.zip` file available on your computer. You can download it from the [GeoNames dump](https://download.geonames.org/export/dump/) page. Once you have the file, you can use the `invenio` CLI to start importing the content:

```shell
invenio geoidentifiers import -v geonames -o allCountries.zip
```

If you want to update the content, or delete a specific one, you can use the `invenio` CLI with the commands `update` and `delete` as presented below:

```shell
invenio geoidentifiers update -v geonames -o allCountries.zip
invenio geoidentifiers delete -v geonames -i geonames::2657896
```

Once loaded, the vocabulary answers on `/api/geoidentifiers`.

## Development

Install the package with its test dependencies:

```shell
pip install -e ".[tests,opensearch2]"
```

`run-tests.sh` starts the database, search and queue containers itself, then runs `check_manifest` and the test suite:

```shell
./run-tests.sh
```

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes, and ensure the tests and the style checks pass before submitting a pull request.

## License

`Invenio Geographic Identifiers` is distributed under the MIT license. See [LICENSE](./LICENSE) for the full text.
