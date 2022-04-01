# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.

## Unreleased

### Added

- Populate MGRS Extension fields
- Populate Grid Extension fields
- Add support for AWS S3 Open Data format (produced by Sinergise)
- change platform and constellation to use best practices (lowercase, no spaces)
- change asset names to use underscore instead of dash

## 0.3.0

## Changed

- updated stactools dependency to version 0.3.0

## Added

- Adding support for Level-1C products

## 0.2.0

### Changed

- Modified Item IDs to include product discriminator ([#7](https://github.com/stactools-packages/sentinel2/pull/7))
- Upgrade to stactools 0.2.1.a2 (supporting PySTAC 1.0.0)
