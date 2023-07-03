# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.

## [0.4.2] - 2023-07-03

## Fixed

- Centroids of antimeridian-crossing MultiPolygons are now computed correctly.

## [0.4.1] - 2023-04-28

### Added

- Projection Extension 'centroid' field

## [0.4.0] - 2023-01-31

### Changed

- remove units where they are 'none'
- update precision for float values
- updated prefix from 'sentinel2' to 's2'
- TCI asset now has role `visual` instead of `data`
- Change platform and constellation to use best practices (lowercase, no spaces)
- Change asset names to use underscore instead of dash
- Band 8A corrected to have common name `nir08` instead of `rededge`
- Asset object keys are now common name rather than band numbers (e.g., `red` instead of `B10`)
- Use black (instead of yapf) for formatting
- pre-commit and isort

### Added

- add "reflectance" to all data asset roles
- add additional sentinel2 properties
- add raster extension
- Populate MGRS Extension fields
- Populate Grid Extension fields
- Add support for AWS S3 Open Data format (produced by Sinergise)
- Band 9 now has common name nir09 and Band 10 has common name cirrus

## [0.3.0] - 2022-03-22

## Changed

- updated stactools dependency to version 0.3.0

## Added

- Adding support for Level-1C products

## [0.2.0] - 2021-07-21

### Changed

- Modified Item IDs to include product discriminator ([#7](https://github.com/stactools-packages/sentinel2/pull/7))
- Upgrade to stactools 0.2.1.a2 (supporting PySTAC 1.0.0)

[Unreleased]: <https://github.com/stactools-packages/sentinel2/compare/v0.4.2..main>
[0.4.2]: <https://github.com/stactools-packages/sentinel2/compare/v0.4.1..v0.4.2>
[0.4.1]: <https://github.com/stactools-packages/sentinel2/compare/v0.4.0..v0.4.1>
[0.4.0]: <https://github.com/stactools-packages/sentinel2/compare/v0.3.0..v0.4.0>
[0.3.0]: <https://github.com/stactools-packages/sentinel2/compare/v0.2.0..v0.3.0>
[0.2.0]: <https://github.com/stactools-packages/sentinel2/releases/tag/v0.2.0>
