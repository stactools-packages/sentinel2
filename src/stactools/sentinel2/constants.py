import pystac
from pystac.link import Link
from pystac.extensions.eo import Band
from typing import Final, List, Dict
from pystac.provider import ProviderRole

SENTINEL2_PROPERTY_PREFIX = "sentinel2"

SENTINEL_LICENSE: Final[Link] = Link(
    rel='license',
    target=
    'https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice'
)

SENTINEL_INSTRUMENTS: Final[List[str]] = ['msi']
SENTINEL_CONSTELLATION: Final[str] = 'sentinel-2'

SENTINEL_PROVIDER: Final[pystac.Provider] = pystac.Provider(
    name='ESA',
    roles=[
        ProviderRole.PRODUCER, ProviderRole.PROCESSOR, ProviderRole.LICENSOR
    ],
    url='https://earth.esa.int/web/guest/home')

SAFE_MANIFEST_ASSET_KEY: Final[str] = "safe_manifest"
INSPIRE_METADATA_ASSET_KEY: Final[str] = "inspire_metadata"
PRODUCT_METADATA_ASSET_KEY: Final[str] = "product_metadata"
GRANULE_METADATA_ASSET_KEY: Final[str] = "granule_metadata"
DATASTRIP_METADATA_ASSET_KEY: Final[str] = "datastrip_metadata"
TILEINFO_METADATA_ASSET_KEY: Final[str] = "tileinfo_metadata"

SENTINEL_BANDS: Final[Dict[str, Band]] = {
    'B01':
    Band.create(name='B01',
                common_name='coastal',
                description='Coastal aerosol (band 1)',
                center_wavelength=0.443,
                full_width_half_max=0.027),
    'B02':
    Band.create(name='B02',
                common_name='blue',
                description='Blue (band 2)',
                center_wavelength=0.490,
                full_width_half_max=0.098),
    'B03':
    Band.create(name='B03',
                common_name='green',
                description='Green (band 3)',
                center_wavelength=0.560,
                full_width_half_max=0.045),
    'B04':
    Band.create(name='B04',
                common_name='red',
                description='Red (band 3)',
                center_wavelength=0.665,
                full_width_half_max=0.038),
    'B05':
    Band.create(name='B05',
                common_name='rededge',
                description='Red edge 1 (band 5)',
                center_wavelength=0.704,
                full_width_half_max=0.019),
    'B06':
    Band.create(name='B06',
                common_name='rededge',
                description='Red edge 2 (band 6)',
                center_wavelength=0.740,
                full_width_half_max=0.018),
    'B07':
    Band.create(name='B07',
                common_name='rededge',
                description='Red edge 3 (band 7)',
                center_wavelength=0.783,
                full_width_half_max=0.028),
    'B08':
    Band.create(name='B08',
                common_name='nir',
                description='NIR 1 (band 8)',
                center_wavelength=0.842,
                full_width_half_max=0.145),
    'B8A':
    Band.create(name='B8A',
                common_name='nir08',
                description='NIR 2 (band 8A)',
                center_wavelength=0.865,
                full_width_half_max=0.033),
    'B09':
    Band.create(name='B09',
                common_name='nir09',
                description='NIR 3 (band 9)',
                center_wavelength=0.945,
                full_width_half_max=0.026),
    'B10':
    Band.create(name='B10',
                common_name='cirrus',
                description='Cirrus (band 10)',
                center_wavelength=1.3735,
                full_width_half_max=0.075),
    'B11':
    Band.create(name='B11',
                common_name='swir16',
                description='SWIR 1 (band 11)',
                center_wavelength=1.610,
                full_width_half_max=0.143),
    'B12':
    Band.create(name='B12',
                common_name='swir22',
                description='SWIR 2 (band 12)',
                center_wavelength=2.190,
                full_width_half_max=0.242),
}

# A dict describing the resolutions that are
# available for each band as separate assets.
# The first resolution is the sensor gsd; others
# are downscaled versions.
BANDS_TO_RESOLUTIONS: Final[Dict[str, List[int]]] = {
    'B01': [60],
    'B02': [10, 20, 60],
    'B03': [10, 20, 60],
    'B04': [10, 20, 60],
    'B05': [20, 60],
    'B06': [20, 60],
    'B07': [20, 60],
    'B08': [10, 20, 60],
    'B8A': [20, 60],
    'B09': [60],
    'B10': [60],
    'B11': [20, 60],
    'B12': [20, 60],
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
