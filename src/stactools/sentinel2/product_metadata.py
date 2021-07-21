from datetime import datetime
import re
from typing import Any, Dict, List, Optional

from shapely.geometry import mapping, Polygon
import pystac
from pystac.utils import str_to_datetime

from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement
from stactools.core.utils import map_opt
from stactools.sentinel2.constants import PRODUCT_METADATA_ASSET_KEY


class ProductMetadataError(Exception):
    pass


def fix_z_values(coord_values: List[str]) -> List[float]:
    """Some geometries have a '0' value in the z position
    of the coordinates. This method detects and removes z
    postion coordinates. This assumes that in cases where
    the z value is included, it is included for all coordinates.
    """
    if len(coord_values) % 3 == 0:
        # Check if all of the 3rd position values are '0'
        # Ignore any blank values
        third_position_is_zero = [
            x == '0' for i, x in enumerate(coord_values) if i % 3 == 2 and x
        ]

        if all(third_position_is_zero):
            # Assuming that all 3rd position coordinates are z values
            # Remove them.
            return [float(c) for i, c in enumerate(coord_values) if i % 3 != 2]

    return [float(c) for c in coord_values if c]


class ProductMetadata:
    def __init__(
            self,
            href,
            read_href_modifier: Optional[ReadHrefModifier] = None) -> None:
        self.href = href
        self._root = XmlElement.from_file(href, read_href_modifier)

        product_info_node = self._root.find('n1:General_Info/Product_Info')
        if product_info_node is None:
            raise ProductMetadataError(
                f"Cannot find product info node for product metadata at {self.href}"
            )
        self.product_info_node = product_info_node

        datatake_node = self.product_info_node.find('Datatake')
        if datatake_node is None:
            raise ProductMetadataError(
                f"Cannot find Datatake node in product metadata at {self.href}"
            )
        self.datatake_node = datatake_node

        granule_node = self.product_info_node.find(
            'Product_Organisation/Granule_List/Granule')
        if granule_node is None:
            raise ProductMetadataError(
                f'Cannot find granule node in product metadata at {self.href}')
        self.granule_node = granule_node

        reflectance_conversion_node = self._root.find(
            'n1:General_Info/Product_Image_Characteristics/Reflectance_Conversion'
        )
        if reflectance_conversion_node is None:
            raise ProductMetadataError(
                f"Could not find reflectance conversion node in product metadata at {self.href}"
            )
        self.reflectance_conversion_node = reflectance_conversion_node

        qa_node = self._root.find('n1:Quality_Indicators_Info')
        if qa_node is None:
            raise ProductMetadataError(
                f"Could not find QA node in product metadata at {self.href}")
        self.qa_node = qa_node

        def _get_geometries():
            geometric_info = self._root.find('n1:Geometric_Info')
            footprint_text = geometric_info.find_text(
                'Product_Footprint/Product_Footprint/Global_Footprint/EXT_POS_LIST'
            )
            if footprint_text is None:
                ProductMetadataError(
                    f'Cannot parse footprint from product metadata at {self.href}'
                )

            footprint_coords = fix_z_values(footprint_text.split(' '))
            footprint_points = [
                p[::-1] for p in list(zip(*[iter(footprint_coords)] * 2))
            ]
            footprint_polygon = Polygon(footprint_points)
            geometry = mapping(footprint_polygon)
            bbox = footprint_polygon.bounds

            return (bbox, geometry)

        self.bbox, self.geometry = _get_geometries()

    @property
    def scene_id(self) -> str:
        """ Returns the string to be used for a STAC Item id.

        Removes the processing number and .SAFE extension
        from the product_id defined below.

        Parsed based on the naming convention found here:
        https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        """
        product_id = self.product_id
        # Ensure the product id (PRODUCT_URI) is as expected.
        if not product_id.endswith('.SAFE'):
            raise ValueError("Unexpected value found at "
                             f"General_Info/Product_Info: {product_id}. "
                             "This was expected to follow the sentinel 2 "
                             "naming convention, including "
                             "ending in .SAFE")
        id_parts = self.product_id.split('_')

        # Remove .SAFE
        id_parts[-1] = id_parts[-1].replace('.SAFE', '')

        # Remove PDGS Processing Baseline number
        id_parts = [part for part in id_parts if not part.startswith('N')]

        return '_'.join(id_parts)

    @property
    def product_id(self) -> str:
        result = self.product_info_node.find_text('PRODUCT_URI')
        if result is None:
            raise ValueError(
                'Cannot determine product ID using product metadata '
                f'at {self.href}')
        else:
            return result

    @property
    def datetime(self) -> datetime:
        time = self.product_info_node.find_text('PRODUCT_START_TIME')
        if time is None:
            raise ValueError(
                'Cannot determine product start time using product metadata '
                f'at {self.href}')
        else:
            return str_to_datetime(time)

    @property
    def image_media_type(self) -> str:
        if self.granule_node.get_attr('imageFormat') == 'GeoTIFF':
            return pystac.MediaType.COG
        else:
            return pystac.MediaType.JPEG2000

    @property
    def image_paths(self) -> List[str]:
        extension = '.tif' if self.image_media_type == pystac.MediaType.COG else '.jp2'

        return [
            f'{x.text}{extension}'
            for x in self.granule_node.findall('IMAGE_FILE')
        ]

    @property
    def relative_orbit(self) -> Optional[int]:
        return map_opt(int,
                       self.datatake_node.find_text('SENSING_ORBIT_NUMBER'))

    @property
    def orbit_state(self) -> Optional[str]:
        return self.datatake_node.find_text('SENSING_ORBIT_DIRECTION')

    @property
    def platform(self) -> Optional[str]:
        return self.datatake_node.find_text('SPACECRAFT_NAME')

    @property
    def mgrs_tile(self) -> Optional[str]:
        m = re.search(r'_T(\d{2}[a-zA-Z]{3})_', self.href)
        return None if m is None else m.group(1)

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        result = {
            's2:product_uri':
            self.product_id,
            's2:generation_time':
            self.product_info_node.find_text('GENERATION_TIME'),
            's2:processing_baseline':
            self.product_info_node.find_text('PROCESSING_BASELINE'),
            's2:product_type':
            self.product_info_node.find_text('PRODUCT_TYPE'),
            's2:datatake_id':
            self.datatake_node.get_attr('datatakeIdentifier'),
            's2:datatake_type':
            self.datatake_node.find_text('DATATAKE_TYPE'),
            's2:datastrip_id':
            self.granule_node.get_attr('datastripIdentifier'),
            's2:granule_id':
            self.granule_node.get_attr('granuleIdentifier'),
            's2:mgrs_tile':
            self.mgrs_tile,
            's2:reflectance_conversion_factor':
            map_opt(float, self.reflectance_conversion_node.find_text('U'))
        }

        return {k: v for k, v in result.items() if v is not None}

    def create_asset(self):
        asset = pystac.Asset(href=self.href,
                             media_type=pystac.MediaType.XML,
                             roles=['metadata'])
        return (PRODUCT_METADATA_ASSET_KEY, asset)
