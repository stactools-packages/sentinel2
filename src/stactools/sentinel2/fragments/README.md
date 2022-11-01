# Fragments

Fragments are JSON files that contain constant values that are included in generated STAC items. Some JSON files also contain information that is used to generate STAC Items, but is not included in the STAC Item. The following fragment types/files exist:

- `sentinel2-c2-l1c` or `-l2a`: Collection data
- `common-assets.json`: Asset data that is common to all Sentinel 2 data products.
- `assets.json`: Surface reflectance or surface temperature asset data.
- `eo-bands.json`: STAC EO extension data for surface reflectance or temperature assets.
- `raster-bands.json`: STAC raster-band extension data for surface reflectance or temperature assets.

