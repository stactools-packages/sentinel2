from typing import Dict, Final, List

import pystac
from pystac.extensions.eo import Band
from pystac.link import Link
from pystac.provider import ProviderRole

SENTINEL2_PROPERTY_PREFIX = "s2"

SENTINEL_LICENSE: Final[Link] = Link(
    rel="license",
    target="https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice",
)

SENTINEL_INSTRUMENTS: Final[List[str]] = ["msi"]
SENTINEL_CONSTELLATION: Final[str] = "sentinel-2"

SENTINEL_PROVIDER: Final[pystac.Provider] = pystac.Provider(
    name="ESA",
    roles=[ProviderRole.PRODUCER, ProviderRole.PROCESSOR, ProviderRole.LICENSOR],
    url="https://earth.esa.int/web/guest/home",
)

SAFE_MANIFEST_ASSET_KEY: Final[str] = "safe_manifest"
INSPIRE_METADATA_ASSET_KEY: Final[str] = "inspire_metadata"
PRODUCT_METADATA_ASSET_KEY: Final[str] = "product_metadata"
GRANULE_METADATA_ASSET_KEY: Final[str] = "granule_metadata"
DATASTRIP_METADATA_ASSET_KEY: Final[str] = "datastrip_metadata"
TILEINFO_METADATA_ASSET_KEY: Final[str] = "tileinfo_metadata"

DEFAULT_TOLERANCE: Final[float] = 0.0001
COORD_ROUNDING: Final[int] = 6

SENTINEL_BANDS: Final[Dict[str, Band]] = {
    "coastal": Band.create(
        name="coastal",
        common_name="coastal",
        description="Coastal aerosol (band 1)",
        center_wavelength=0.443,
        full_width_half_max=0.027,
    ),
    "blue": Band.create(
        name="blue",
        common_name="blue",
        description="Blue (band 2)",
        center_wavelength=0.490,
        full_width_half_max=0.098,
    ),
    "green": Band.create(
        name="green",
        common_name="green",
        description="Green (band 3)",
        center_wavelength=0.560,
        full_width_half_max=0.045,
    ),
    "red": Band.create(
        name="red",
        common_name="red",
        description="Red (band 4)",
        center_wavelength=0.665,
        full_width_half_max=0.038,
    ),
    "rededge1": Band.create(
        name="rededge1",
        common_name="rededge",
        description="Red edge 1 (band 5)",
        center_wavelength=0.704,
        full_width_half_max=0.019,
    ),
    "rededge2": Band.create(
        name="rededge2",
        common_name="rededge",
        description="Red edge 2 (band 6)",
        center_wavelength=0.740,
        full_width_half_max=0.018,
    ),
    "rededge3": Band.create(
        name="rededge3",
        common_name="rededge",
        description="Red edge 3 (band 7)",
        center_wavelength=0.783,
        full_width_half_max=0.028,
    ),
    "nir": Band.create(
        name="nir",
        common_name="nir",
        description="NIR 1 (band 8)",
        center_wavelength=0.842,
        full_width_half_max=0.145,
    ),
    "nir08": Band.create(
        name="nir08",
        common_name="nir08",
        description="NIR 2 (band 8A)",
        center_wavelength=0.865,
        full_width_half_max=0.033,
    ),
    "nir09": Band.create(
        name="nir09",
        common_name="nir09",
        description="NIR 3 (band 9)",
        center_wavelength=0.945,
        full_width_half_max=0.026,
    ),
    "cirrus": Band.create(
        name="cirrus",
        common_name="cirrus",
        description="Cirrus (band 10)",
        center_wavelength=1.3735,
        full_width_half_max=0.075,
    ),
    "swir16": Band.create(
        name="swir16",
        common_name="swir16",
        description="SWIR 1 (band 11)",
        center_wavelength=1.610,
        full_width_half_max=0.143,
    ),
    "swir22": Band.create(
        name="swir22",
        common_name="swir22",
        description="SWIR 2 (band 12)",
        center_wavelength=2.190,
        full_width_half_max=0.242,
    ),
}

# A dict describing the resolutions that are
# available for each band as separate assets.
# The first resolution is the sensor gsd; others
# are downscaled versions.
UNSUFFIXED_BAND_RESOLUTION: Final[Dict[str, int]] = {
    "coastal": 60,
    "blue": 10,
    "green": 10,
    "red": 10,
    "rededge1": 20,
    "rededge2": 20,
    "rededge3": 20,
    "nir": 10,
    "nir08": 20,
    "nir09": 60,
    "cirrus": 60,
    "swir16": 20,
    "swir22": 20,
}

BANDS_TO_ASSET_NAME: Final[Dict[str, str]] = {
    "B01": "coastal",
    "B02": "blue",
    "B03": "green",
    "B04": "red",
    "B05": "rededge1",
    "B06": "rededge2",
    "B07": "rededge3",
    "B08": "nir",
    "B8A": "nir08",
    "B09": "nir09",
    "B10": "cirrus",
    "B11": "swir16",
    "B12": "swir22",
}

L2A_IMAGE_PATHS: Final[List[str]] = [
    "preview.jpg",
    "R10m/B04.jp2",
    "R10m/B03.jp2",
    "R10m/B02.jp2",
    "R10m/WVP.jp2",
    "R10m/AOT.jp2",
    "R10m/TCI.jp2",
    "R10m/B08.jp2",
    "R20m/B12.jp2",
    "R20m/B06.jp2",
    "R20m/B07.jp2",
    "R20m/B05.jp2",
    "R20m/B11.jp2",
    "R20m/B04.jp2",
    "R20m/B03.jp2",
    "R20m/B02.jp2",
    "R20m/WVP.jp2",
    "R20m/B8A.jp2",
    "R20m/SCL.jp2",
    "R20m/AOT.jp2",
    "R20m/TCI.jp2",
    "R20m/B08.jp2",
    "R60m/B12.jp2",
    "R60m/B06.jp2",
    "R60m/B07.jp2",
    "R60m/B05.jp2",
    "R60m/B11.jp2",
    "R60m/B04.jp2",
    "R60m/B01.jp2",
    "R60m/B03.jp2",
    "R60m/B02.jp2",
    "R60m/WVP.jp2",
    "R60m/B8A.jp2",
    "R60m/SCL.jp2",
    "R60m/AOT.jp2",
    "R60m/B09.jp2",
    "R60m/TCI.jp2",
    "R60m/B08.jp2",
]

L1C_IMAGE_PATHS: Final[List[str]] = [
    "preview.jpg",
    "B01.jp2",
    "B02.jp2",
    "B03.jp2",
    "B04.jp2",
    "B05.jp2",
    "B06.jp2",
    "B07.jp2",
    "B08.jp2",
    "B8A.jp2",
    "B09.jp2",
    "B10.jp2",
    "B11.jp2",
    "B12.jp2",
    "TCI.jp2",
]
