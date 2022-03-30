import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Pattern, Final, Any
from datetime import datetime

import pystac
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.sat import OrbitState, SatExtension
from stactools.sentinel2.mgrs import MgrsExtension

from stactools.core.io import ReadHrefModifier
from stactools.core.projection import transform_from_bbox
from stactools.sentinel2.safe_manifest import SafeManifest
from stactools.sentinel2.product_metadata import ProductMetadata
from stactools.sentinel2.granule_metadata import GranuleMetadata
from stactools.sentinel2.utils import extract_gsd
from stactools.sentinel2.constants import (
    BANDS_TO_RESOLUTIONS, DATASTRIP_METADATA_ASSET_KEY, SENTINEL_PROVIDER,
    SENTINEL_LICENSE, SENTINEL_BANDS, SENTINEL_INSTRUMENTS,
    SENTINEL_CONSTELLATION, INSPIRE_METADATA_ASSET_KEY)

logger = logging.getLogger(__name__)

MGRS_PATTERN: Final[Pattern[str]] = re.compile(
    r"_T(\d{1,2})([CDEFGHJKLMNPQRSTUVWX])([ABCDEFGHJKLMNPQRSTUVWXYZ][ABCDEFGHJKLMNPQRSTUV])_"
)


@dataclass
class Metadata:
    scene_id: str
    cloudiness_percentage: Optional[float]
    extra_assets: Dict[str, pystac.Asset]
    geometry: Dict[str, Any]
    bbox: List[float]
    datetime: datetime
    platform: str
    orbit_state: str
    relative_orbit: int
    metadata_dict: Dict[str, Any]
    image_media_type: str
    image_paths: List[str]
    epsg: int
    proj_bbox: List[float]
    resolution_to_shape: Dict[int, Tuple[int, int]]


def create_item(
        granule_href: str,
        additional_providers: Optional[List[pystac.Provider]] = None,
        read_href_modifier: Optional[ReadHrefModifier] = None) -> pystac.Item:
    """Create a STC Item from a Sentinel 2 granule.

    Arguments:
        granule_href: The HREF to the granule. This is expected to be a path
            to a SAFE archive, e.g. https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/01/C/CV/2016/03/27/S2A_MSIL2A_20160327T204522_N0212_R128_T01CCV_20210214T042702.SAFE,
            or a partial S3 object path, e.g. s3://sentinel-s2-l2a/tiles/10/S/DG/2018/12/31/0/
        additional_providers: Optional list of additional providers to set into the Item
        read_href_modifier: A function that takes an HREF and returns a modified HREF.
            This can be used to modify a HREF to make it readable, e.g. appending
            an Azure SAS token or creating a signed URL.

    Returns:
        pystac.Item: An item representing the Sentinel 2 scene
    """  # noqa

    metadata: Optional[Metadata] = None
    if granule_href.lower().endswith(".safe"):
        metadata = metadata_from_safe_manifest(granule_href,
                                               read_href_modifier)

    item = pystac.Item(id=metadata.scene_id,
                       geometry=metadata.geometry,
                       bbox=metadata.bbox,
                       datetime=metadata.datetime,
                       properties={})

    # --Common metadata--

    item.common_metadata.providers = [SENTINEL_PROVIDER]

    if additional_providers is not None:
        item.common_metadata.providers.extend(additional_providers)

    item.common_metadata.platform = metadata.platform
    item.common_metadata.constellation = SENTINEL_CONSTELLATION
    item.common_metadata.instruments = SENTINEL_INSTRUMENTS

    # --Extensions--

    # eo
    eo = EOExtension.ext(item, add_if_missing=True)
    eo.cloud_cover = metadata.cloudiness_percentage

    # sat
    sat = SatExtension.ext(item, add_if_missing=True)
    sat.orbit_state = OrbitState(metadata.orbit_state.lower())
    sat.relative_orbit = metadata.relative_orbit

    # proj
    projection = ProjectionExtension.ext(item, add_if_missing=True)
    projection.epsg = metadata.epsg
    if projection.epsg is None:
        raise ValueError(
            f'Could not determine EPSG code for {granule_href}; which is required.'
        )

    # mgrs
    mgrs_match = MGRS_PATTERN.search(metadata.scene_id)
    if mgrs_match and len(mgrs_match.groups()) == 3:
        mgrs_groups = mgrs_match.groups()
        mgrs = MgrsExtension.ext(item, add_if_missing=True)
        mgrs.utm_zone = int(mgrs_groups[0])
        mgrs.latitude_band = mgrs_groups[1]
        mgrs.grid_square = mgrs_groups[2]
    else:
        logger.error(
            f'Error populating MGRS Extension fields from ID: {metadata.scene_id}'
        )

    # s2 properties
    item.properties.update(metadata.metadata_dict)

    # --Assets--

    image_assets = dict([
        image_asset_from_href(os.path.join(granule_href, image_path),
                              metadata.resolution_to_shape, metadata.proj_bbox,
                              metadata.image_media_type)
        for image_path in metadata.image_paths
    ])

    for key, asset in image_assets.items():
        assert key not in item.assets
        item.add_asset(key, asset)

    # --Links--

    item.links.append(SENTINEL_LICENSE)

    return item


def image_asset_from_href(
        asset_href: str,
        resolution_to_shape: Dict[int, Tuple[int, int]],
        proj_bbox: List[float],
        media_type: Optional[str] = None) -> Tuple[str, pystac.Asset]:
    logger.debug(f'Creating asset for image {asset_href}')

    _, ext = os.path.splitext(asset_href)
    if media_type is not None:
        asset_media_type = media_type
    else:
        if ext.lower() == '.jp2':
            asset_media_type = pystac.MediaType.JPEG2000
        elif ext.lower() in ['.tiff', '.tif']:
            asset_media_type = pystac.MediaType.GEOTIFF
        else:
            raise Exception(
                f'Must supply a media type for asset : {asset_href}')

    # Handle preview image

    if '_PVI' in asset_href:
        asset = pystac.Asset(href=asset_href,
                             media_type=asset_media_type,
                             title='True color preview',
                             roles=['data'])
        asset_eo = EOExtension.ext(asset)
        asset_eo.bands = [
            SENTINEL_BANDS['B04'], SENTINEL_BANDS['B03'], SENTINEL_BANDS['B02']
        ]
        return 'preview', asset

    # Extract gsd and proj info
    resolution = 0
    try:
        # extracting GSD from filename is only possible for Level 2
        resolution = extract_gsd(asset_href)
    except ValueError:
        # in Level-1C we can deduct the spatial resolution from the band ID or
        # asset name
        band_id_search = re.search(r'_(B\w{2})', asset_href)
        if band_id_search is not None:
            resolution = BANDS_TO_RESOLUTIONS[band_id_search.groups()[0]][0]
        elif '_TCI' in asset_href:
            resolution = 10.0

    shape = list(resolution_to_shape[int(resolution)])
    transform = transform_from_bbox(proj_bbox, shape)

    def set_asset_properties(_asset: pystac.Asset,
                             _band_gsd: Optional[int] = None):
        if _band_gsd:
            pystac.CommonMetadata(_asset).gsd = _band_gsd
        asset_projection = ProjectionExtension.ext(_asset)
        asset_projection.shape = shape
        asset_projection.bbox = proj_bbox
        asset_projection.transform = transform

    # Handle band image

    band_id_search = re.search(r'_(B\w{2})', asset_href)
    if band_id_search is not None:
        try:
            band_id, href_res = os.path.splitext(asset_href)[0].split('_')[-2:]
            band = SENTINEL_BANDS[band_id]
        except KeyError:
            # Level-1C have different names
            band_id = os.path.splitext(asset_href)[0].split('_')[-1]
            band = SENTINEL_BANDS[band_id]
            href_res = f'{BANDS_TO_RESOLUTIONS[band_id_search.groups()[0]][0]}m'

        # Get the asset resolution from the file name.
        # If the asset resolution is the band GSD, then
        # include the gsd information for that asset. Otherwise,
        # do not include the GSD information in the asset
        # as this may be confusing for users given that the
        # raster spatial resolution and gsd will differ.
        # See https://github.com/radiantearth/stac-spec/issues/1096
        asset_res = int(href_res.replace('m', ''))
        band_gsd: Optional[int] = None
        if asset_res == BANDS_TO_RESOLUTIONS[band_id][0]:
            asset_key = band_id
            band_gsd = asset_res
        else:
            # If this isn't the default resolution, use the raster
            # resolution in the asset key.
            # TODO: Use the raster extension and spatial_resolution
            # property to encode the spatial resolution of all assets.
            asset_key = f'{band_id}_{asset_res}m'

        asset = pystac.Asset(href=asset_href,
                             media_type=asset_media_type,
                             title=f'{band.description} - {href_res}',
                             roles=['data'])

        asset_eo = EOExtension.ext(asset)
        asset_eo.bands = [SENTINEL_BANDS[band_id]]
        set_asset_properties(asset, band_gsd)
        return asset_key, asset

    # Handle auxiliary images

    if '_TCI' in asset_href:
        # True color
        asset = pystac.Asset(href=asset_href,
                             media_type=asset_media_type,
                             title='True color image',
                             roles=['data'])
        asset_eo = EOExtension.ext(asset)
        asset_eo.bands = [
            SENTINEL_BANDS['B04'], SENTINEL_BANDS['B03'], SENTINEL_BANDS['B02']
        ]
        set_asset_properties(asset)

        maybe_res = asset_href[-7:-4]
        if re.match(r'(\w{2}m)', maybe_res):
            return f'visual-{maybe_res}', asset
        else:
            return 'visual', asset

    if '_AOT_' in asset_href:
        # Aerosol
        asset = pystac.Asset(href=asset_href,
                             media_type=asset_media_type,
                             title='Aerosol optical thickness (AOT)',
                             roles=['data'])
        set_asset_properties(asset)
        return f'AOT-{asset_href[-7:-4]}', asset

    if '_WVP_' in asset_href:
        # Water vapor
        asset = pystac.Asset(href=asset_href,
                             media_type=asset_media_type,
                             title='Water vapour (WVP)',
                             roles=['data'])
        set_asset_properties(asset)
        return f'WVP-{asset_href[-7:-4]}', asset

    if '_SCL_' in asset_href:
        # Classification map
        asset = pystac.Asset(href=asset_href,
                             media_type=asset_media_type,
                             title='Scene classfication map (SCL)',
                             roles=['data'])
        set_asset_properties(asset)
        return f'SCL-{asset_href[-7:-4]}', asset

    raise ValueError(f'Unexpected asset: {asset_href}')


def metadata_from_safe_manifest(
        granule_href: str, read_href_modifier: Optional[ReadHrefModifier]):
    safe_manifest = SafeManifest(granule_href, read_href_modifier)
    product_metadata = ProductMetadata(safe_manifest.product_metadata_href,
                                       read_href_modifier)
    granule_metadata = GranuleMetadata(safe_manifest.granule_metadata_href,
                                       read_href_modifier)
    extra_assets = dict([
        safe_manifest.create_asset(),
        product_metadata.create_asset(),
        granule_metadata.create_asset(),
        (INSPIRE_METADATA_ASSET_KEY,
         pystac.Asset(href=safe_manifest.inspire_metadata_href,
                      media_type=pystac.MediaType.XML,
                      roles=['metadata'])),
        (DATASTRIP_METADATA_ASSET_KEY,
         pystac.Asset(href=safe_manifest.datastrip_metadata_href,
                      media_type=pystac.MediaType.XML,
                      roles=['metadata'])),
    ])

    if safe_manifest.thumbnail_href is not None:
        extra_assets["preview"] = pystac.Asset(
            href=safe_manifest.thumbnail_href,
            media_type=pystac.MediaType.COG,
            roles=['thumbnail'])

    return Metadata(
        scene_id=product_metadata.scene_id,
        cloudiness_percentage=granule_metadata.cloudiness_percentage,
        extra_assets=extra_assets,
        geometry=product_metadata.geometry,
        bbox=product_metadata.bbox,
        datetime=product_metadata.datetime,
        platform=product_metadata.platform,
        orbit_state=product_metadata.orbit_state,
        relative_orbit=product_metadata.relative_orbit,
        metadata_dict={
            **product_metadata.metadata_dict,
            **granule_metadata.metadata_dict
        },
        image_media_type=product_metadata.image_media_type,
        image_paths=product_metadata.image_paths,
        epsg=granule_metadata.epsg,
        proj_bbox=granule_metadata.proj_bbox,
        resolution_to_shape=granule_metadata.resolution_to_shape)
