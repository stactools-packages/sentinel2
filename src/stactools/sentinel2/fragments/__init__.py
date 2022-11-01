import json
from typing import Any, Dict, Optional

import pkg_resources
from pystac import Asset, Extent, Link, MediaType, Provider, Summaries
from pystac.extensions.item_assets import AssetDefinition
from pystac.utils import make_absolute_href


class CollectionFragments:
    """Class for accessing collection data."""

    def __init__(self, collection_id: str):
        """Initialize a new group of fragments for the provided Sensor."""
        self._id = collection_id

    def collection(self) -> Dict[str, Any]:
        """Loads the collection.json for the given collection id.
        Converts some elements to pystac object.
        Returns:
            Dict[str, Any]: Dict from parsed JSON with some converted fields.
        """
        data: Dict[str, Any] = self._load()
        data["extent"] = Extent.from_dict(data["extent"])
        data["providers"] = [
            Provider.from_dict(provider) for provider in data["providers"]
        ]
        data["links"] = [Link.from_dict(link) for link in data["links"]]
        data["summaries"] = Summaries(data["summaries"])

        assets = {}
        for key, asset_dict in data["item_assets"].items():
            media_type = asset_dict.get("type")
            asset_dict["type"] = MediaType[media_type]
            assets[key] = AssetDefinition(asset_dict)
        data["item_assets"] = assets
        return data

    def _load(self) -> Any:
        try:
            with pkg_resources.resource_stream(
                "stactools.sentinel2.fragments", f"collections/{self._id}.json"
            ) as stream:
                return json.load(stream)
        except FileNotFoundError as e:
            raise e


class Fragments:
    """Class for accessing asset and extension data."""

    def __init__(
        self,
        sensor: str,
        satellite: int,
        base_href: str,
        # level1_radiance: Dict[str, Dict[str, Optional[float]]],
    ):
        """Initialize a new group of fragments for the provided Sensor."""
        self._sensor = sensor
        self._satellite = satellite
        self.base_href = base_href
        # self.level1_radiance = level1_radiance

    def common_assets(self) -> Dict[str, Any]:
        """Loads common-assets.json.
        Converts the loaded dicts to STAC Assets.
        Returns:
            Dict[str, Asset]: Dict of Assets keys and Assets.
        """
        asset_dicts = self._load("common-assets.json", "common")
        assets = self._convert_assets(asset_dicts)
        return assets

    def eo_bands(self) -> Dict[str, Any]:
        """Loads the eo-bands.json.
        Returns:
            Dict[str, Dict]: Dict of Assets keys and EO Extension dicts.
        """
        eo: Dict[str, Any] = self._load("eo-bands.json")
        return eo

    def raster_bands(self) -> Dict[str, Any]:
        """Loads the st-raster-bands.json.
        Returns:
            Dict[str, Dict]: Dict of Assets keys and Raster Extension dicts.
        """
        raster: Dict[str, Any] = self._load("raster-bands.json")
        return raster

    def _convert_assets(self, asset_dicts: Dict[str, Any]) -> Dict[str, Asset]:
        assets = {}
        for key, asset_dict in asset_dicts.items():
            media_type = asset_dict.pop("type", None)
            if media_type is not None:
                asset_dict["type"] = MediaType[media_type]
            else:
                asset_dict["type"] = MediaType.COG

            href_suffix = asset_dict.pop("href_suffix", None)
            if href_suffix is not None:
                href = f"{self.base_href}_{href_suffix}"
            else:
                href = f"{self.base_href}_{key.upper()}.jp2"
            asset_dict["href"] = make_absolute_href(href)
            assets[key] = Asset.from_dict(asset_dict)

        return assets

    def _load(self, file_name: str, dir_name: Optional[str] = None) -> Any:
        if dir_name is None:
            dir_name = self._sensor.lower()
        try:
            with pkg_resources.resource_stream(
                "stactools.sentinel2.fragments", f"{dir_name}/{file_name}"
            ) as stream:
                return json.load(stream)
        except FileNotFoundError as e:
            raise e
