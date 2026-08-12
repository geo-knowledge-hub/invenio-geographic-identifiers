# Changes

## Version 0.4.0 (2024-02-22)

Released as `0.4.0.dev0`; recorded here after the fact.

- Pinned `invenio-i18n` to keep `flask-babelex` available;
- Added the `extras` field, and search the suggester against it;
- Support for multiple location names in the schema;
- Reworked the GeoNames transform operation.

## Version 0.3.0 (2023-02-21)

Recorded here after the fact.

- Replaced `elasticsearch7` with `opensearch2`, and updated the dependencies accordingly;
- Updated the CI workflow.

## Version 0.2.0 (2022-08-10)

- Updated Invenio vocabularies

  - Support for InvenioRDM 9.0;
  - Updated `ZippedCSVReader` with the new DataStream API features;
  - Updated `GeoNames` DataStream configuration to support multiple readers.

## Version 0.1.1 (2022-07-19)

- Fixed scheme name (replaced `GeoNames` with `geonames`) to be compatible with
  `RDM_RECORDS_LOCATION_SCHEMES` (Invenio RDM Records).

## Version 0.1.0 (2022-07-17)

- Initial implementation of the Geographic Identifiers vocabularies for InvenioRDM;
- DataStreams API

  - Readers/Writers/Transformers to handle geographic datasets.

- Supported identifier schemes (contrib module)

  - [GeoNames](https://www.geonames.org/)

- Implementation spec

  - Support for InvenioRDM 8.0;
  - Based on [Invenio Vocabularies](https://github.com/inveniosoftware/invenio-vocabularies).
