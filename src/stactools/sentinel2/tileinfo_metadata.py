import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pystac
from pystac.utils import str_to_datetime
from shapely.geometry import shape
from stactools.core.io import ReadHrefModifier, read_text

from stactools.sentinel2.constants import SENTINEL2_PROPERTY_PREFIX as s2_prefix
from stactools.sentinel2.constants import TILEINFO_METADATA_ASSET_KEY


class TileInfoMetadataError(Exception):
    pass


class TileInfoMetadata:
    def __init__(self, href, read_href_modifier: Optional[ReadHrefModifier] = None):
        self.href = href
        self.tileinfo = json.loads(read_text(self.href, read_href_modifier))

        self._datetime = str_to_datetime(self.tileinfo["timestamp"])
        self._geometry = self.tileinfo["tileDataGeometry"]
        self._bbox = shape(self._geometry).bounds
        self._product_path = self.tileinfo["productPath"]

    @property
    def product_path(self) -> str:
        return self._product_path

    @property
    def geometry(self) -> Dict[str, Any]:
        return self._geometry

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return self._bbox

    @property
    def datetime(self) -> datetime:
        return self._datetime

    @property
    def metadata_dict(self):
        product_type = None
        product_name = self.tileinfo.get("productName")
        if product_name and "_MSIL2A_" in product_name:
            product_type = "S2MSI2A"
        elif product_name and "_MSIL1C_" in product_name:
            product_type = "S2MSI1C"

        result = {f"{s2_prefix}:product_type": product_type}

        return {k: v for k, v in result.items() if v is not None}

    def create_asset(self):
        asset = pystac.Asset(
            href=self.href, media_type=pystac.MediaType.JSON, roles=["metadata"]
        )
        return TILEINFO_METADATA_ASSET_KEY, asset
