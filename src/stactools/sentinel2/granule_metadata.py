from typing import Dict, List, Optional, Tuple

import pystac
from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement
from stactools.core.utils import map_opt

from stactools.sentinel2.constants import GRANULE_METADATA_ASSET_KEY
from stactools.sentinel2.constants import SENTINEL2_PROPERTY_PREFIX as s2_prefix


class GranuleMetadataError(Exception):
    pass


class GranuleMetadata:
    def __init__(self, href, read_href_modifier: Optional[ReadHrefModifier] = None):
        self.href = href

        self._root = XmlElement.from_file(href, read_href_modifier)

        tile_id = self._root.find_text("n1:General_Info/TILE_ID")
        if tile_id is None:
            raise GranuleMetadataError(
                f"Cannot find granule tile_id granule metadata at {self.href}"
            )
        self.tile_id = tile_id

        geocoding_node = self._root.find("n1:Geometric_Info/Tile_Geocoding")
        if geocoding_node is None:
            raise GranuleMetadataError(f"Cannot find geocoding node in {self.href}")
        self._geocoding_node = geocoding_node

        tile_angles_node = self._root.find("n1:Geometric_Info/Tile_Angles")
        if tile_angles_node is None:
            raise GranuleMetadataError(f"Cannot find tile angles node in {self.href}")
        self._tile_angles_node = tile_angles_node

        self._viewing_angle_nodes = self._tile_angles_node.findall(
            "Mean_Viewing_Incidence_Angle_List/Mean_Viewing_Incidence_Angle"
        )

        self._image_content_node = self._root.find(
            "n1:Quality_Indicators_Info/Image_Content_QI"
        )

        self.resolution_to_shape: Dict[int, Tuple[int, int]] = {}
        for size_node in self._geocoding_node.findall("Size"):
            res = size_node.get_attr("resolution")
            if res is None:
                raise GranuleMetadataError("Size element does not have resolution.")
            nrows = map_opt(int, size_node.find_text("NROWS"))
            if nrows is None:
                raise GranuleMetadataError(
                    f"Could not get rows from size for resolution {res}"
                )
            ncols = map_opt(int, size_node.find_text("NCOLS"))
            if ncols is None:
                raise GranuleMetadataError(
                    f"Could not get columns from size for resolution {res}"
                )
            self.resolution_to_shape[int(res)] = (nrows, ncols)

    @property
    def epsg(self) -> Optional[int]:
        epsg_str = self._geocoding_node.find_text("HORIZONTAL_CS_CODE")
        if epsg_str is None:
            return None
        else:
            return int(epsg_str.split(":")[1])

    @property
    def proj_bbox(self) -> List[float]:
        """The bbox of the image in the CRS of the image data"""
        nrows, ncols = self.resolution_to_shape[10]
        geoposition = self._geocoding_node.find("Geoposition")
        if geoposition is None:
            raise GranuleMetadataError(f"Cannot find geoposition node in {self.href}")
        ulx = map_opt(float, geoposition.find_text("ULX"))
        if ulx is None:
            raise GranuleMetadataError("Could not get upper left X coordinate")
        uly = map_opt(float, geoposition.find_text("ULY"))
        if uly is None:
            raise GranuleMetadataError("Could not get upper left Y coordinate")

        return [ulx, uly - (10 * nrows), ulx + (10 * ncols), uly]

    @property
    def cloudiness_percentage(self) -> Optional[float]:
        return map_opt(
            float, self._image_content_node.find_text("CLOUDY_PIXEL_PERCENTAGE")
        )

    @property
    def mean_solar_zenith(self) -> Optional[float]:
        return map_opt(
            float, self._tile_angles_node.find_text("Mean_Sun_Angle/ZENITH_ANGLE")
        )

    @property
    def mean_solar_azimuth(self) -> Optional[float]:
        return map_opt(
            float, self._tile_angles_node.find_text("Mean_Sun_Angle/AZIMUTH_ANGLE")
        )

    @property
    def metadata_dict(self):
        properties: Dict[str, Optional[float]] = {
            f"{s2_prefix}:degraded_msi_data_percentage": map_opt(
                float,
                self._image_content_node.find_text("DEGRADED_MSI_DATA_PERCENTAGE"),
            ),
            f"{s2_prefix}:nodata_pixel_percentage": map_opt(
                float, self._image_content_node.find_text("NODATA_PIXEL_PERCENTAGE")
            ),
            f"{s2_prefix}:saturated_defective_pixel_percentage": map_opt(
                float,
                self._image_content_node.find_text(
                    "SATURATED_DEFECTIVE_PIXEL_PERCENTAGE"
                ),
            ),
            f"{s2_prefix}:dark_features_percentage": map_opt(
                float, self._image_content_node.find_text("DARK_FEATURES_PERCENTAGE")
            ),
            f"{s2_prefix}:cloud_shadow_percentage": map_opt(
                float, self._image_content_node.find_text("CLOUD_SHADOW_PERCENTAGE")
            ),
            f"{s2_prefix}:vegetation_percentage": map_opt(
                float, self._image_content_node.find_text("VEGETATION_PERCENTAGE")
            ),
            f"{s2_prefix}:not_vegetated_percentage": map_opt(
                float, self._image_content_node.find_text("NOT_VEGETATED_PERCENTAGE")
            ),
            f"{s2_prefix}:water_percentage": map_opt(
                float, self._image_content_node.find_text("WATER_PERCENTAGE")
            ),
            f"{s2_prefix}:unclassified_percentage": map_opt(
                float, self._image_content_node.find_text("UNCLASSIFIED_PERCENTAGE")
            ),
            f"{s2_prefix}:medium_proba_clouds_percentage": map_opt(
                float,
                self._image_content_node.find_text("MEDIUM_PROBA_CLOUDS_PERCENTAGE"),
            ),
            f"{s2_prefix}:high_proba_clouds_percentage": map_opt(
                float,
                self._image_content_node.find_text("HIGH_PROBA_CLOUDS_PERCENTAGE"),
            ),
            f"{s2_prefix}:thin_cirrus_percentage": map_opt(
                float, self._image_content_node.find_text("THIN_CIRRUS_PERCENTAGE")
            ),
            f"{s2_prefix}:snow_ice_percentage": map_opt(
                float, self._image_content_node.find_text("SNOW_ICE_PERCENTAGE")
            ),
        }

        return {k: v for k, v in properties.items() if v is not None}

    @property
    def product_id(self) -> str:
        return self.tile_id

    @property
    def scene_id(self) -> str:
        """Returns the string to be used for a STAC Item id.

        Removes the processing number and .SAFE extension
        from the product_id defined below.

        Parsed based on the naming convention found here:
        https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        """
        # Ensure the product id (PRODUCT_URI) is as expected.
        id_parts = self.product_id.split("_")

        # Remove PDGS Processing Baseline number
        id_parts = [part for part in id_parts if not part.startswith("N")]

        return "_".join(id_parts)

    @property
    def platform(self) -> Optional[str]:
        if self.tile_id.startswith("S2A"):
            return "sentinel-2a"
        elif self.tile_id.startswith("S2B"):
            return "sentinel-2b"
        else:
            return None

    def create_asset(self):
        asset = pystac.Asset(
            href=self.href, media_type=pystac.MediaType.XML, roles=["metadata"]
        )
        return GRANULE_METADATA_ASSET_KEY, asset
