# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.

## [Unreleased]

Nothing

## [0.2.1] - 2023-05-24

### Added

- `antimeridian_strategy` option to `create_item` to split or normalize Item geometries that cross the antimeridian ([#99](https://github.com/stactools-packages/sentinel2/pull/99))
- `coordinate_precision` option to `create_item` to round Item geometry coordinates and bbox values ([#99](https://github.com/stactools-packages/sentinel2/pull/99))

## [0.2.0] - 2021-07-21

### Changed

- Modified Item IDs to include product discriminator ([#7](https://github.com/stactools-packages/sentinel2/pull/7))
- Upgrade to stactools 0.2.1.a2 (supporting PySTAC 1.0.0)

[Unreleased]: <https://github.com/stactools-packages/sentinel2/compare/v0.2.1..v0.2>
[0.2.1]: <https://github.com/stactools-packages/sentinel2/compare/v0.2.0..v0.2.1>
[0.2.0]: <https://github.com/stactools-packages/sentinel2/releases/tag/v0.2.0>
