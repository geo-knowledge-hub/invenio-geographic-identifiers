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

The vocabulary, its REST resource, its search mapping, its import job and its database tables are all registered automatically. The one thing an instance has to declare is where the datastreams come from, because the readers, transformers and writers are resolved by name from the application configuration. For this, in your `invenio.cfg` you can include the values defined by the package:

```python
from invenio_vocabularies.config import (
    VOCABULARIES_DATASTREAM_READERS,
    VOCABULARIES_DATASTREAM_TRANSFORMERS,
    VOCABULARIES_DATASTREAM_WRITERS,
)

from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    VOCABULARIES_DATASTREAM_READERS as GEONAMES_READERS,
    VOCABULARIES_DATASTREAM_TRANSFORMERS as GEONAMES_TRANSFORMERS,
    VOCABULARIES_DATASTREAM_WRITERS as GEONAMES_WRITERS,
)

VOCABULARIES_DATASTREAM_READERS = {**VOCABULARIES_DATASTREAM_READERS, **GEONAMES_READERS}
VOCABULARIES_DATASTREAM_TRANSFORMERS = {**VOCABULARIES_DATASTREAM_TRANSFORMERS, **GEONAMES_TRANSFORMERS}
VOCABULARIES_DATASTREAM_WRITERS = {**VOCABULARIES_DATASTREAM_WRITERS, **GEONAMES_WRITERS}
```

Merging the `invenio_vocabularies` values rather than replacing them is not optional. `InvenioVocabularies` registers its own with `setdefault`, and the configuration file is read first, so a bare `{**GEONAMES_READERS}` removes every reader, transformer and writer InvenioRDM ships, including the ones the ROR, OpenAIRE and ORCID vocabularies need.

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

## Loading the full dump

`allCountries.zip` holds `13,446,834` rows. Reading and transforming all of them takes under two minutes on one core. Writing them is what takes the time, because every entry is validated, stored and indexed. The import can therefore be split across workers, and it should be.

### Splitting the work

A run can be divided into shards. Each shard reads the whole dump but keeps only its own rows, so between them they cover it exactly once:

```shell
# One shard, in this process. Run these in parallel however you like
invenio geoidentifiers import -v geonames -o allCountries.zip --shards 8 --shard 0

# Or hand every shard to a Celery worker
invenio geoidentifiers import -v geonames -o allCountries.zip --shards 8 --celery
```

Shards are numbered from 0. The rows a shard covers depend only on its number and on how many shards there are, so a shard that fails can be re-run on its own without disturbing the others.

### Draining the indexer queue

Batched writing does not index inline. It publishes record ids to a queue that something else has to consume:

```shell
invenio index run
```

Run it alongside the import, or in a loop after it. Without it the records land in the database and the search index stays empty.

### Importing only what you need

More than half of GeoNames consists of streams, farm buildings, hillsides and stretches of road. The `--feature-classes` option narrows a run to the classes an instance actually serves:

```shell
invenio geoidentifiers import -v geonames -o allCountries.zip --feature-classes P,A
```

The table below gives the meaning of each feature class available in GeoNames:

| classes | rows | meaning |
|---|---:|---|
| `P` | 5,215,299 | populated places |
| `H` | 2,610,403 | streams, lakes |
| `S` | 2,543,712 | spots, buildings, farms |
| `T` | 1,837,270 | mountains, hills |
| `A` | 543,475 | administrative divisions |
| `L` | 494,213 | parks, areas |
| `V` | 123,702 | forest, vegetation |
| `R` | 58,170 | roads, railroads |
| `U` | 15,587 | undersea |
| `P,A` | **5,758,774** | **place names and the divisions containing them** |

If `--feature-classes` is not given, everything is imported.

### From the administration interface

The import is also registered as an InvenioRDM v13 job, `Import GeoNames`, so it can be run from the administration interface instead of the command line.

Note that InvenioRDM does not ship the scheduler beat that dispatches job runs. [It has to be deployed per instance](https://inveniordm.docs.cern.ch/operate/customize/jobs/). Without one, nothing runs from the administration interface. The CLI needs no such thing.

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
