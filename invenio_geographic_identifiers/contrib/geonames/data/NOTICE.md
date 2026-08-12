# GeoNames lookup tables

The two tab-separated files in this directory are redistributed from the GeoNames gazetteer. They let the transformer turn the opaque codes in a GeoNames dump into labels a user interface can display `PPLA` into "seat of a first-order administrative division", `CH.ZH` into "Zurich".

| File | Source | Retrieved | Upstream `Last-Modified` |
| --- | --- | --- | --- |
| `featureCodes_en.txt` | <https://download.geonames.org/export/dump/featureCodes_en.txt> | 2026-08-11 | 2026-08-11 |
| `admin1CodesASCII.txt` | <https://download.geonames.org/export/dump/admin1CodesASCII.txt> | 2026-08-11 | 2026-08-11 |

## Licence

This work is licensed under a [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), © GeoNames.

The data is provided "as is" without warranty or any representation of accuracy, timeliness or completeness.

## Why these are vendored

Both tables are small (58 KB and 148 KB) and change on the order of months, so a checked-in snapshot keeps imports offline and reproducible.

`admin2Codes.txt` is deliberately **not** vendored: at 2.3 MB and 47,000 rows it is an order of magnitude larger, and second-order divisions are empty for most places. The raw `admin2` code is stored instead.

Resolving administrative codes without these files is not an option. GeoNames documents `admin1_code` as a "fipscode (subject to change to iso code)", so it is not ISO 3166-2 and cannot be looked up with `pycountry`: for `FR.11` GeoNames means Île-de-France while `pycountry` returns Aude, and `IT.07`, `BR.27` and `DE.01` resolve to nothing at all. Country codes are genuine ISO 3166-1 alpha-2, so those still come from `pycountry`.

## Refreshing

Download both files from the URLs above, replace them here, and update the dates in the table. Keep the format byte-for-byte as published. `lookups.py` parses the upstream column layout directly.
