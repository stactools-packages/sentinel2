# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.

## [Unreleased]

### Added

- Added a `classification:classes` field to the `scl` asset (SCL).

## [0.6.4] - 2024-04-04

### Added

- Added a `raster:bands` field to the `visual` asset (TCI).

## [0.6.3] - 2024-02-01

### Changed

- Scenes that produce a geometry that has an unreasonably large area now raise and exception
  rather than producing an item with that incorrect geometry.

## [0.6.2] - 2024-01-08

### Fixed

- ViewExtension handles NaN values for viewing_angles correctly.

## [0.6.1] - 2024-01-04

### Fixed

- if tileinfo metadata is missing tileDataGeometry field, throw a ValueError with a meaningful
  message instead of an unintentional KeyError

### Changed

- use reproject_shape instead of reproject_geom (deprecated)

## [0.6.0] - 2023-12-13

### Fixed

- Antimeridian-crossing scene bboxes

## Removed

- `create_item` method parameter `create_item` removed, as it was no longer used

## [0.5.0] - 2023-12-01

### Added

- Add `https://stac-extensions.github.io/sentinel-2/v1.0.0/schema.json` conformance class
- Add `s2:tile_id` field
- `product_metadata` asset ([#117](https://github.com/stactools-packages/sentinel2/pull/117))
- Examples ([#124](https://github.com/stactools-packages/sentinel2/pull/124))
- `cloud` and `snow` assets ([#129](https://github.com/stactools-packages/sentinel2/pull/129))
- gsd for ancillary assets (e.g., aot, wvp, etc) ([#139](https://github.com/stactools-packages/sentinel2/pull/139))
- Mean values for sensor azimuth and incidence angle in Item properties ([#137](https://github.com/stactools-packages/sentinel2/pull/141))
- Add PVI asset as "preview" for Sentinel-2 L2A ([#143](https://github.com/stactools-packages/sentinel2/pull/143))

### Fixed

- Antimeridian handling (again) ([#122](https://github.com/stactools-packages/sentinel2/pull/122))
- Populate `created` property with a valid RFC 3339 datetime ([#125](https://github.com/stactools-packages/sentinel2/pull/125))
- stactools required version should be >=0.5.2 instead of >= 0.4.8 ([#125](https://github.com/stactools-packages/sentinel2/pull/125))
- Roles fixed, 'reflectance' removed from auxiliary assets (e.g., wvp, aot)

### Changed

- The convention for naming the STAC Items has changed. ([#131](https://github.com/stactools-packages/sentinel2/pull/131)). A full explanation given in [Issue #130](https://github.com/stactools-packages/sentinel2/issues/130)
- pystac >= 1.9.0 is now required
- Names in eo:bands structure are now S2 band names, not common name ([#139](https://github.com/stactools-packages/sentinel2/pull/139))
- PVI asset role changed from "thumbnail" or "visual" to "overview" ([#143](https://github.com/stactools-packages/sentinel2/pull/143))
- Removed asset "thumbnail" pointing to preview.jpg asset, as this file frequently
  does not exit. ([#144](https://github.com/stactools-packages/sentinel2/pull/144))

### Removed

- Removes `s2:granule_id`
- Removes `s2:mgrs_tile` field, as this is covered by both the MRGS Extension and Grid Extension fields
- Drop support for Python 3.9
- raster:bands.bits_per_pixel ([#139](https://github.com/stactools-packages/sentinel2/pull/139))
- Band descriptions ([#139](https://github.com/stactools-packages/sentinel2/pull/139))
- Per asset sensor azimuth and incidence angles ([#137](https://github.com/stactools-packages/sentinel2/pull/141))

## [0.4.2] - 2023-07-03

### Fixed

- Antimeridian-crossing geometries are now valid.
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

<!-- [Unreleased]: <https://github.com/stactools-packages/sentinel2/compare/v0.6.3..main> -->
[0.6.4]: <https://github.com/stactools-packages/sentinel2/compare/v0.6.3..v0.6.4>
[0.6.3]: <https://github.com/stactools-packages/sentinel2/compare/v0.6.2..v0.6.3>
[0.6.2]: <https://github.com/stactools-packages/sentinel2/compare/v0.6.1..v0.6.2>
[0.6.1]: <https://github.com/stactools-packages/sentinel2/compare/v0.6.0..v0.6.1>
[0.6.0]: <https://github.com/stactools-packages/sentinel2/compare/v0.5.0..v0.6.0>
[0.5.0]: <https://github.com/stactools-packages/sentinel2/compare/v0.4.2..v0.5.0>
[0.4.2]: <https://github.com/stactools-packages/sentinel2/compare/v0.4.1..v0.4.2>
[0.4.1]: <https://github.com/stactools-packages/sentinel2/compare/v0.4.0..v0.4.1>
[0.4.0]: <https://github.com/stactools-packages/sentinel2/compare/v0.3.0..v0.4.0>
[0.3.0]: <https://github.com/stactools-packages/sentinel2/compare/v0.2.0..v0.3.0>
[0.2.0]: <https://github.com/stactools-packages/sentinel2/releases/tag/v0.2.0>
