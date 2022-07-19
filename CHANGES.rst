..
    Copyright (C) 2022 GEO Secretariat.

    invenio-geographic-identifiers is free software; you can redistribute
    it and/or modify it under the terms of the MIT License; see LICENSE file
    for more details.

Changes
=======

Version 0.1.1 (2022-07-19)
--------------------------

- Fixed scheme name (Replaced ``GeoNames`` to ``geonames``) to be compatible with ``RDM_RECORDS_LOCATION_SCHEMES`` (Invenio RDM Records)

Version 0.1.0 (2022-07-17)
--------------------------

- Initial implementation of the Geographic Identifiers vocabularies for the InvenioRDM;
- DataStreams API

  - Readers/Writers/Transformers to handle geographic datasets.
  
- Supported Identifier schemes (Contrib module)

  - `Geonames <https://www.geonames.org/>`_

- Implementation spec

  - Support for InvenioRDM 8.0;
  - Based on `Invenio Vocabularies <https://github.com/inveniosoftware/invenio-vocabularies>`_ module.
