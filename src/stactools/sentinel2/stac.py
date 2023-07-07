import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from itertools import chain
from typing import Any, Dict, Final, List, Optional, Pattern, Tuple

import pystac
import shapely
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.grid import GridExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import DataType, RasterBand, RasterExtension
from pystac.extensions.sat import OrbitState, SatExtension
from pystac.extensions.view import ViewExtension
from shapely.geometry import mapping as shapely_mapping
from shapely.geometry import shape as shapely_shape
from shapely.validation import make_valid
from stactools.core.io import ReadHrefModifier
from stactools.core.projection import reproject_geom, transform_from_bbox
from stactools.core.utils import antimeridian
from stactools.core.utils.antimeridian import Strategy

from stactools.sentinel2.constants import (
    BANDS_TO_ASSET_NAME,
    COORD_ROUNDING,
    DATASTRIP_METADATA_ASSET_KEY,
    DEFAULT_TOLERANCE,
    INSPIRE_METADATA_ASSET_KEY,
    L1C_IMAGE_PATHS,
    L2A_IMAGE_PATHS,
)
from stactools.sentinel2.constants import SENTINEL2_PROPERTY_PREFIX as s2_prefix
from stactools.sentinel2.constants import (
    SENTINEL_BANDS,
    SENTINEL_CONSTELLATION,
    SENTINEL_INSTRUMENTS,
    SENTINEL_LICENSE,
    SENTINEL_PROVIDER,
    UNSUFFIXED_BAND_RESOLUTION,
)
from stactools.sentinel2.granule_metadata import GranuleMetadata, ViewingAngle
from stactools.sentinel2.mgrs import MgrsExtension
from stactools.sentinel2.product_metadata import ProductMetadata
from stactools.sentinel2.safe_manifest import SafeManifest
from stactools.sentinel2.tileinfo_metadata import TileInfoMetadata
from stactools.sentinel2.utils import extract_gsd

logger = logging.getLogger(__name__)

MGRS_PATTERN: Final[Pattern[str]] = re.compile(
    r"_T(\d{1,2})([CDEFGHJKLMNPQRSTUVWX])([ABCDEFGHJKLMNPQRSTUVWXYZ][ABCDEFGHJKLMNPQRSTUV])"
)

TCI_PATTERN: Final[Pattern[str]] = re.compile(r"[_/]TCI[_.]")
AOT_PATTERN: Final[Pattern[str]] = re.compile(r"[_/]AOT[_.]")
WVP_PATTERN: Final[Pattern[str]] = re.compile(r"[_/]WVP[_.]")
SCL_PATTERN: Final[Pattern[str]] = re.compile(r"[_/]SCL[_.]")
THUMBNAIL_PATTERN: Final[Pattern[str]] = re.compile(r"[_/]preview[_.]")

BAND_PATTERN: Final[Pattern[str]] = re.compile(r"[_/](B\w{2})")
IS_TCI_PATTERN: Final[Pattern[str]] = re.compile(r"[_/]TCI")
BAND_ID_PATTERN: Final[Pattern[str]] = re.compile(r"[_/](B\d[A\d])")
RESOLUTION_PATTERN: Final[Pattern[str]] = re.compile(r"(\w{2}m)")

RGB_BANDS: Final[List[Band]] = [
    SENTINEL_BANDS["red"],
    SENTINEL_BANDS["green"],
    SENTINEL_BANDS["blue"],
]

DEFAULT_SCALE = 0.0001


@dataclass(frozen=True)
class Metadata:
    scene_id: str
    cloudiness_percentage: Optional[float]
    extra_assets: Dict[str, pystac.Asset]
    geometry: Dict[str, Any]
    bbox: List[float]
    datetime: datetime
    platform: str
    metadata_dict: Dict[str, Any]
    image_media_type: str
    image_paths: List[str]
    epsg: int
    proj_bbox: List[float]
    resolution_to_shape: Dict[int, Tuple[int, int]]
    processing_baseline: str
    viewing_angles: Dict[str, ViewingAngle]
    orbit_state: Optional[str] = None
    relative_orbit: Optional[int] = None
    sun_azimuth: Optional[float] = None
    sun_zenith: Optional[float] = None
    boa_add_offsets: Optional[Dict[str, int]] = None


def create_item(
    granule_href: str,
    tolerance: float = DEFAULT_TOLERANCE,
    additional_providers: Optional[List[pystac.Provider]] = None,
    read_href_modifier: Optional[ReadHrefModifier] = None,
    asset_href_prefix: Optional[str] = None,
    antimeridian_strategy: Strategy = Strategy.SPLIT,
) -> pystac.Item:
    """Create a STC Item from a Sentinel 2 granule.

    Arguments:
        granule_href: The HREF to the granule. This is expected to be a path
            to a SAFE archive, e.g. https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/01/C/CV/2016/03/27/S2A_MSIL2A_20160327T204522_N0212_R128_T01CCV_20210214T042702.SAFE,
            or a partial S3 object path, e.g. s3://sentinel-s2-l2a/tiles/10/S/DG/2018/12/31/0/
        tolerance: Determines the level of simplification of the geometry
        additional_providers: Optional list of additional providers to set into the Item
        read_href_modifier: A function that takes an HREF and returns a modified HREF.
            This can be used to modify a HREF to make it readable, e.g. appending
            an Azure SAS token or creating a signed URL.
        asset_href_prefix: The URL prefix to apply to the asset hrefs
        antimeridian_strategy (Antimeridian): Either split on -180 or
            normalize geometries so all longitudes are either positive or
            negative.

    Returns:
        pystac.Item: An item representing the Sentinel 2 scene
    """  # noqa

    if granule_href.lower().endswith(".safe"):
        metadata = metadata_from_safe_manifest(granule_href, read_href_modifier)
    else:
        metadata = metadata_from_granule_metadata(
            granule_href, read_href_modifier, tolerance
        )
    created = datetime.now().strftime("%Y-%m-%dT%H:%MZ")

    # ensure that we have a valid geometry
    geometry = shapely_mapping(make_valid(shapely_shape(metadata.geometry)))

    item = pystac.Item(
        id=metadata.scene_id,
        geometry=geometry,
        bbox=metadata.bbox,
        datetime=metadata.datetime,
        properties={"created": created},
    )

    # Handle antimeridian if necessary
    antimeridian.fix_item(item, antimeridian_strategy)

    # --Common metadata--

    item.common_metadata.providers = [SENTINEL_PROVIDER]

    if additional_providers is not None:
        item.common_metadata.providers.extend(additional_providers)

    item.common_metadata.platform = metadata.platform.lower()
    item.common_metadata.constellation = SENTINEL_CONSTELLATION
    item.common_metadata.instruments = SENTINEL_INSTRUMENTS

    # --Extensions--

    # eo
    eo = EOExtension.ext(item, add_if_missing=True)
    eo.cloud_cover = metadata.cloudiness_percentage
    RasterExtension.add_to(item)

    # sat
    if metadata.orbit_state or metadata.relative_orbit:
        sat = SatExtension.ext(item, add_if_missing=True)
        sat.orbit_state = (
            OrbitState(metadata.orbit_state.lower()) if metadata.orbit_state else None
        )
        sat.relative_orbit = metadata.relative_orbit

    # Projection Extension
    projection = ProjectionExtension.ext(item, add_if_missing=True)
    projection.epsg = metadata.epsg
    if projection.epsg is None:
        raise ValueError(
            f"Could not determine EPSG code for {granule_href}; which is required."
        )

    # It is assumed that any MultiPolygon is an antimeridian-crossing scene.
    # If we used split, the code below "normalizes" the polygon with negative longitude to
    # have positive longitude greater than 180, then takes the centroid of this new
    # MultiPolygon, and the un-normalize it back to within (-180,180).
    if (
        antimeridian_strategy == Strategy.SPLIT
        and item.geometry
        and item.geometry.get("type") == "MultiPolygon"
    ):
        shapely_geometry = shapely_shape(item.geometry)
        # force all positive lons so we can merge on an antimeridian split
        polys = list(shapely_geometry.geoms)
        for index, poly in enumerate(polys):
            coords = list(poly.exterior.coords)
            lons = [coord[0] for coord in coords]
            if min(lons) < 0:
                polys[index] = shapely.affinity.translate(poly, xoff=+360)

        # make_valid merges the normalized MultiPolygon into a single normalized Polygon
        # and removes any line artifacts that may exist.
        normalized_geometry = make_valid(shapely.geometry.MultiPolygon(polys))

        centroid = normalized_geometry.centroid
        lon = centroid.x
        if lon > 180:
            lon = lon - 360
    else:
        centroid = shapely_shape(item.geometry).centroid
        lon = centroid.x

    projection.centroid = {"lat": round(centroid.y, 5), "lon": round(lon, 5)}

    # MGRS and Grid Extension
    mgrs_match = MGRS_PATTERN.search(metadata.scene_id)
    if mgrs_match and len(mgrs_groups := mgrs_match.groups()) == 3:
        mgrs = MgrsExtension.ext(item, add_if_missing=True)
        mgrs.utm_zone = int(mgrs_groups[0])
        mgrs.latitude_band = mgrs_groups[1]
        mgrs.grid_square = mgrs_groups[2]
        grid = GridExtension.ext(item, add_if_missing=True)
        grid.code = f"MGRS-{mgrs.utm_zone}{mgrs.latitude_band}{mgrs.grid_square}"
    else:
        logger.error(
            f"Error populating MGRS and Grid Extensions fields from ID: {metadata.scene_id}"
        )

    # View Extension

    # both sun_azimuth and sun_zenith can be NaN, so don't set
    # when that is the case
    if (msa := metadata.sun_azimuth) and not math.isnan(msa):
        view = ViewExtension.ext(item, add_if_missing=True)
        view.sun_azimuth = msa

    if (msz := metadata.sun_zenith) and not math.isnan(msz):
        view = ViewExtension.ext(item, add_if_missing=True)
        view.sun_elevation = 90 - msz

    # s2 properties
    item.properties.update(metadata.metadata_dict)

    # --Assets--

    image_assets = dict(
        [
            image_asset_from_href(
                item=item,
                asset_href=os.path.join(asset_href_prefix or granule_href, image_path),
                resolution_to_shape=metadata.resolution_to_shape,
                proj_bbox=metadata.proj_bbox,
                media_type=metadata.image_media_type,
                processing_baseline=metadata.processing_baseline,
                viewing_angles=metadata.viewing_angles,
                boa_add_offsets=metadata.boa_add_offsets,
            )
            for image_path in metadata.image_paths
        ]
    )

    for key, asset in chain(image_assets.items(), metadata.extra_assets.items()):
        assert key not in item.assets
        item.add_asset(key, asset)

    # --Links--

    item.links.append(SENTINEL_LICENSE)

    return item


def image_asset_from_href(
    item: pystac.Item,
    asset_href: str,
    resolution_to_shape: Dict[int, Tuple[int, int]],
    proj_bbox: List[float],
    media_type: Optional[str],
    processing_baseline: str,
    viewing_angles: Dict[str, ViewingAngle],
    boa_add_offsets: Optional[Dict[str, int]] = None,
) -> Tuple[str, pystac.Asset]:
    logger.debug(f"Creating asset for image {asset_href}")

    _, ext = os.path.splitext(asset_href)
    if media_type is not None:
        asset_media_type = media_type
    else:
        if ext.lower() == ".jp2":
            asset_media_type = pystac.MediaType.JPEG2000
        elif ext.lower() in [".tiff", ".tif"]:
            asset_media_type = pystac.MediaType.GEOTIFF
        else:
            raise Exception(f"Must supply a media type for asset : {asset_href}")

    # Handle preview image

    if "_PVI" in asset_href:
        asset = pystac.Asset(
            href=asset_href,
            media_type=asset_media_type,
            title="True color preview",
            roles=["data", "reflectance"],
        )
        asset_eo = EOExtension.ext(asset)
        asset_eo.bands = RGB_BANDS
        return "preview", asset
    elif THUMBNAIL_PATTERN.search(asset_href):
        # thumbnail image
        asset = pystac.Asset(
            href=asset_href,
            media_type=pystac.MediaType.JPEG,
            title="Thumbnail image",
            roles=["thumbnail"],
        )
        return "thumbnail", asset

    # Extract gsd and proj info
    resolution = extract_gsd(asset_href)
    if resolution is None:
        # in Level-1C we can deduct the spatial resolution from the band ID or
        # asset name
        band_id_search = BAND_PATTERN.search(asset_href)
        if band_id_search:
            resolution = highest_asset_res(band_id_search.group(1))
        elif IS_TCI_PATTERN.search(asset_href):
            resolution = 10

    shape = list(resolution_to_shape[int(resolution)])
    transform = transform_from_bbox(proj_bbox, shape)

    def set_asset_properties(_asset: pystac.Asset, _band_gsd: Optional[int] = None):
        if _band_gsd:
            pystac.CommonMetadata(_asset).gsd = _band_gsd
        asset_projection = ProjectionExtension.ext(_asset)
        asset_projection.shape = shape
        asset_projection.bbox = proj_bbox
        asset_projection.transform = transform

    # Handle band image

    band_id_search = BAND_ID_PATTERN.search(asset_href)
    if band_id_search:
        try:
            band_id = band_id_search.group(1)
            asset_res = resolution
            band = band_from_band_id(band_id)
        except KeyError:
            # Level-1C have different names
            band_id = os.path.splitext(asset_href)[0].split("_")[-1]
            band = band_from_band_id(band_id)
            asset_res = highest_asset_res(band_id_search.group(1))

        # Get the asset resolution from the file name.
        # If the asset resolution is the band GSD, then
        # include the gsd information for that asset. Otherwise,
        # do not include the GSD information in the asset
        # as this may be confusing for users given that the
        # raster spatial resolution and gsd will differ.
        # See https://github.com/radiantearth/stac-spec/issues/1096
        band_gsd: Optional[int] = None
        if asset_res == highest_asset_res(band_id):
            asset_id = BANDS_TO_ASSET_NAME[band_id]
            band_gsd = asset_res
        else:
            # If this isn't the default resolution, use the raster
            # resolution in the asset key.
            # TODO: Use the raster extension and spatial_resolution
            # property to encode the spatial resolution of all assets.
            asset_id = f"{BANDS_TO_ASSET_NAME[band_id]}_{int(asset_res)}m"

        asset = pystac.Asset(
            href=asset_href,
            media_type=asset_media_type,
            title=f"{band.description} - {asset_res}m",
            roles=["data", "reflectance"],
        )
        viewing_angle = viewing_angles[band_id]
        # We can't use the ViewExtension here until
        # https://github.com/stac-utils/pystac/issues/793 is fixed
        if not math.isnan(viewing_angle.azimuth):
            # View Extension doesn't specify fields in Assets,
            # but if it does, this should be uncommented
            # ViewExtension.ext(item, add_if_missing=True)
            asset.extra_fields["view:azimuth"] = viewing_angle.azimuth

        if not math.isnan(viewing_angle.zenith):
            # View Extension doesn't specify fields in Assets,
            # but if it does, this should be uncommented
            # ViewExtension.ext(item, add_if_missing=True)
            asset.extra_fields["view:incidence_angle"] = viewing_angle.zenith

        asset_eo = EOExtension.ext(asset)
        asset_eo.bands = [band_from_band_id(band_id)]
        set_asset_properties(asset, band_gsd)

        RasterExtension.ext(asset).bands = raster_bands(
            boa_add_offsets, processing_baseline, band_id, resolution
        )

    # Handle auxiliary images
    elif TCI_PATTERN.search(asset_href):
        # True color
        asset = pystac.Asset(
            href=asset_href,
            media_type=asset_media_type,
            title="True color image",
            roles=["visual"],
        )
        asset_eo = EOExtension.ext(asset)
        asset_eo.bands = RGB_BANDS
        set_asset_properties(asset)

        maybe_res = extract_gsd(asset_href)
        asset_id = f"visual_{maybe_res}m" if maybe_res and maybe_res != 10 else "visual"
    elif AOT_PATTERN.search(asset_href):
        # Aerosol
        asset = pystac.Asset(
            href=asset_href,
            media_type=asset_media_type,
            title="Aerosol optical thickness (AOT)",
            roles=["data", "reflectance"],
        )
        set_asset_properties(asset)

        RasterExtension.ext(asset).bands = [
            RasterBand.create(
                nodata=0,
                spatial_resolution=resolution,
                data_type=DataType.UINT16,
                bits_per_sample=15,
                scale=0.001,
                offset=0,
            )
        ]

        maybe_res = extract_gsd(asset_href)
        asset_id = mk_asset_id(maybe_res, "aot")
    elif WVP_PATTERN.search(asset_href):
        # Water vapor
        asset = pystac.Asset(
            href=asset_href,
            media_type=asset_media_type,
            title="Water vapour (WVP)",
            roles=["data", "reflectance"],
        )
        set_asset_properties(asset)

        RasterExtension.ext(asset).bands = [
            RasterBand.create(
                nodata=0,
                spatial_resolution=resolution,
                data_type=DataType.UINT16,
                bits_per_sample=15,
                unit="cm",
                scale=0.001,
                offset=0,
            )
        ]

        maybe_res = extract_gsd(asset_href)
        asset_id = mk_asset_id(maybe_res, "wvp")
    elif SCL_PATTERN.search(asset_href):
        # Classification map
        asset = pystac.Asset(
            href=asset_href,
            media_type=asset_media_type,
            title="Scene classification map (SCL)",
            roles=["data", "reflectance"],
        )
        set_asset_properties(asset)

        RasterExtension.ext(asset).bands = [
            RasterBand.create(
                nodata=0,
                spatial_resolution=resolution,
                data_type=DataType.UINT8,
            )
        ]

        maybe_res = extract_gsd(asset_href)
        asset_id = mk_asset_id(maybe_res, "scl")
    else:
        raise ValueError(f"Unexpected asset: {asset_href}")

    return asset_id, asset


def band_from_band_id(band_id):
    return SENTINEL_BANDS[BANDS_TO_ASSET_NAME[band_id]]


def highest_asset_res(band_id: str) -> int:
    return UNSUFFIXED_BAND_RESOLUTION[BANDS_TO_ASSET_NAME[band_id]]


def mk_asset_id(maybe_res: Optional[int], name: str):
    return f"{name.lower()}_{maybe_res}m" if maybe_res and maybe_res != 20 else name


# this is used for SAFE archive format
def metadata_from_safe_manifest(
    granule_href: str, read_href_modifier: Optional[ReadHrefModifier]
) -> Metadata:
    safe_manifest = SafeManifest(granule_href, read_href_modifier)
    product_metadata = ProductMetadata(
        safe_manifest.product_metadata_href, read_href_modifier
    )
    granule_metadata = GranuleMetadata(
        safe_manifest.granule_metadata_href, read_href_modifier
    )
    extra_assets = dict(
        [
            safe_manifest.create_asset(),
            product_metadata.create_asset(),
            granule_metadata.create_asset(),
            (
                INSPIRE_METADATA_ASSET_KEY,
                pystac.Asset(
                    href=safe_manifest.inspire_metadata_href,
                    media_type=pystac.MediaType.XML,
                    roles=["metadata"],
                ),
            ),
            (
                DATASTRIP_METADATA_ASSET_KEY,
                pystac.Asset(
                    href=safe_manifest.datastrip_metadata_href,
                    media_type=pystac.MediaType.XML,
                    roles=["metadata"],
                ),
            ),
        ]
    )

    if granule_metadata.pvi_filename is not None:
        extra_assets["preview"] = pystac.Asset(
            href=os.path.join(granule_href, granule_metadata.pvi_filename),
            media_type=product_metadata.image_media_type,
            roles=["thumbnail"],
        )

    return Metadata(
        scene_id=product_metadata.scene_id,
        extra_assets=extra_assets,
        geometry=product_metadata.geometry,
        bbox=[round(v, COORD_ROUNDING) for v in product_metadata.bbox],
        datetime=product_metadata.datetime,
        platform=product_metadata.platform,
        orbit_state=product_metadata.orbit_state,
        relative_orbit=product_metadata.relative_orbit,
        metadata_dict={
            **product_metadata.metadata_dict,
            **granule_metadata.metadata_dict,
        },
        image_media_type=product_metadata.image_media_type,
        image_paths=product_metadata.image_paths,
        cloudiness_percentage=granule_metadata.cloudiness_percentage,
        epsg=granule_metadata.epsg,
        proj_bbox=[round(v, COORD_ROUNDING) for v in granule_metadata.proj_bbox],
        resolution_to_shape=granule_metadata.resolution_to_shape,
        sun_zenith=granule_metadata.mean_solar_zenith,
        sun_azimuth=granule_metadata.mean_solar_azimuth,
        processing_baseline=granule_metadata.processing_baseline,
        boa_add_offsets=product_metadata.boa_add_offsets,
        viewing_angles=granule_metadata.viewing_angles,
    )


# this is used for the Sinergise S3 format,
# e.g., s3://sentinel-s2-l1c/tiles/10/S/DG/2018/12/31/0/
def metadata_from_granule_metadata(
    granule_metadata_href: str,
    read_href_modifier: Optional[ReadHrefModifier],
    tolerance: float,
) -> Metadata:
    granule_metadata = GranuleMetadata(
        os.path.join(granule_metadata_href, "metadata.xml"), read_href_modifier
    )
    tileinfo_metadata = TileInfoMetadata(
        os.path.join(granule_metadata_href, "tileInfo.json"), read_href_modifier
    )

    product_metadata = None
    if os.path.exists(f := os.path.join(granule_metadata_href, "product_metadata.xml")):
        product_metadata = ProductMetadata(f, read_href_modifier)
    elif granule_metadata_href.startswith("https://roda.sentinel-hub.com"):
        f = (
            granule_metadata_href.split("tiles/")[0]
            + tileinfo_metadata.product_path
            + "/metadata.xml"
        )
        product_metadata = ProductMetadata(f, read_href_modifier)

    geometry = shapely_shape(
        reproject_geom(
            f"epsg:{granule_metadata.epsg}", "epsg:4326", tileinfo_metadata.geometry
        )
    ).simplify(tolerance)

    extra_assets = dict(
        [
            granule_metadata.create_asset(),
            tileinfo_metadata.create_asset(),
        ]
    )

    image_paths = (
        L2A_IMAGE_PATHS if "_L2A_" in granule_metadata.scene_id else L1C_IMAGE_PATHS
    )

    metadata_dict = {
        **granule_metadata.metadata_dict,
        **tileinfo_metadata.metadata_dict,
        f"{s2_prefix}:processing_baseline": granule_metadata.processing_baseline,
    }
    if product_metadata is not None:
        metadata_dict.update(**product_metadata.metadata_dict)

    return Metadata(
        scene_id=granule_metadata.scene_id,
        extra_assets=extra_assets,
        metadata_dict=metadata_dict,
        cloudiness_percentage=granule_metadata.cloudiness_percentage,
        epsg=granule_metadata.epsg,
        proj_bbox=granule_metadata.proj_bbox,
        resolution_to_shape=granule_metadata.resolution_to_shape,
        geometry=shapely_mapping(geometry),
        bbox=geometry.bounds,
        datetime=tileinfo_metadata.datetime,
        platform=granule_metadata.platform,
        image_media_type=pystac.MediaType.JPEG2000,
        image_paths=image_paths,
        sun_zenith=granule_metadata.mean_solar_zenith,
        sun_azimuth=granule_metadata.mean_solar_azimuth,
        processing_baseline=granule_metadata.processing_baseline,
        boa_add_offsets=product_metadata.boa_add_offsets if product_metadata else None,
        viewing_angles=granule_metadata.viewing_angles,
    )


def offset_for_pb(processing_baseline: str) -> float:
    if processing_baseline < "04.00":
        return 0
    else:
        return -0.1


def raster_bands(
    boa_add_offsets: Optional[Dict[str, int]],
    processing_baseline: str,
    band_id: str,
    resolution: float,
) -> List[RasterBand]:
    # prior to processing baseline 04.00, scale and offset were
    # defined out of band, so handle that case
    offset = (
        round(boa_add_offsets[band_id] * DEFAULT_SCALE, 6)
        if boa_add_offsets
        else offset_for_pb(processing_baseline)
    )

    return [
        RasterBand.create(
            nodata=0,
            spatial_resolution=resolution,
            data_type=DataType.UINT16,
            bits_per_sample=15,
            scale=DEFAULT_SCALE,
            offset=offset,
        )
    ]
