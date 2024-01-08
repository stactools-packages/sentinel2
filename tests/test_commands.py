# ruff: noqa: E501

import os
import re
from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Final, List

import pystac
import pytest
from click import Group
from click.testing import CliRunner
from pystac.extensions.eo import EOExtension
from pystac.extensions.grid import GridExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
from pystac.utils import is_absolute_href
from shapely.geometry import box, mapping, shape
from stactools.core.projection import reproject_shape
from stactools.sentinel2.commands import create_sentinel2_command
from stactools.sentinel2.constants import (
    COORD_ROUNDING,
    SENTINEL_BANDS,
)
from stactools.sentinel2.constants import SENTINEL2_PROPERTY_PREFIX as s2_prefix
from stactools.sentinel2.mgrs import MgrsExtension
from stactools.sentinel2.utils import extract_gsd

from tests import test_data

BANDS_TO_RESOLUTIONS: Final[Dict[str, List[int]]] = {
    # asset coastal is 60, coastal_20m is 20, as 20m wasn't added until 2021/22
    "B01": [60, 20],
    "B02": [10, 20, 60],
    "B03": [10, 20, 60],
    "B04": [10, 20, 60],
    "B05": [20, 60],
    "B06": [20, 60],
    "B07": [20, 60],
    "B08": [10, 20, 60],
    "B8A": [20, 60],
    "B09": [60],
    "B10": [60],
    "B11": [20, 60],
    "B12": [20, 60],
}
ID_TO_FILE_NAME = {
    "S2A_T46RER_20210908T043714_L1C": "S2A_MSIL1C_20210908T042701_N0301_R133_T46RER_20210908T070248.SAFE",
    "S2A_T07HFE_20190212T192646_L2A": "S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE",
    "S2B_T01CCV_20191228T210521_L2A": "S2B_MSIL2A_20191228T210519_N0212_R071_T01CCV_20201003T104658.SAFE",
    "S2B_T22HBD_20210122T133224_L2A": "esa_S2B_MSIL2A_20210122T133229_N0214_R081_T22HBD_20210122T155500.SAFE",
    "S2B_T33XWJ_20220413T150756_L2A": "S2B_MSIL2A_20220413T150759_N0400_R025_T33XWJ_20220414T082126.SAFE",
    "S2A_OPER_MSI_L2A_TL_SGS__20181231T210250_A018414_T10SDG": "S2A_OPER_MSI_L2A_TL_SGS__20181231T210250_A018414_T10SDG",
    "S2A_OPER_MSI_L1C_TL_SGS__20181231T203637_A018414_T10SDG": "S2A_OPER_MSI_L1C_TL_SGS__20181231T203637_A018414_T10SDG",
    "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBP": "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBP",
    "S2A_T34LBQ_20220401T090142_L2A": "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ",
    # antimeridian-crossing scene
    "S2A_T01LAC_20200717T221944_L1C": "S2A_MSIL1C_20200717T221941_R029_T01LAC_20200717T234135.SAFE",
    # antimeridian-crossing scene with positive lon centroid
    "S2A_T01WCP_20230625T234624_L2A": "S2A_MSIL2A_20230625T234621_N0509_R073_T01WCP_20230626T022157.SAFE",
    # antimeridian-crossing scene with negative lon centroid
    "S2A_T01WCS_20230625T234624_L2A": "S2A_MSIL2A_20230625T234621_N0509_R073_T01WCS_20230626T022157.SAFE",
    # both sun_azimuth and sun_zenith can be NaN, so don't set
    # "S2A_T01WCP_20230625T234624_L2A": "S2A_MSIL2A_20230625T234621_N0509_R073_T01WCP_20230626T022158.SAFE",
    # viewing angles are all NaN, so don't set
    "S2A_OPER_MSI_L2A_TL_2APS_20240108T121951_A044635_T34VEL": "S2A_OPER_MSI_L2A_TL_2APS_20240108T121951_A044635_T34VEL",
}


def proj_bbox_area_difference(item):
    projection = ProjectionExtension.ext(item)
    visual_asset = item.assets.get("visual_10m") or item.assets.get("visual")
    asset_projection = ProjectionExtension.ext(visual_asset)
    pb = mapping(box(*asset_projection.bbox))
    proj_geom = reproject_shape(f"epsg:{projection.epsg}", "epsg:4326", pb)

    item_geom = shape(item.geometry)

    difference_area = item_geom.difference(proj_geom).area
    raster_area = proj_geom.area

    # We expect the footprint to be in the raster
    # bounds, so any difference should be relatively very low
    # and due to reprojection.
    return difference_area / raster_area


@pytest.mark.parametrize("item_id,file_name", ID_TO_FILE_NAME.items())
def test_create_item(tmp_path: Path, item_id: str, file_name: str):
    granule_href = test_data.get_path(f"data-files/{file_name}")
    runner = CliRunner()
    runner.invoke(
        create_sentinel2_command(Group()),
        ["create-item", granule_href, str(tmp_path)],
    )
    jsons = [p for p in os.listdir(tmp_path) if p.endswith(".json")]
    assert len(jsons) == 1
    file_name = jsons[0]
    item = pystac.Item.from_file(str(tmp_path / file_name))
    item.validate()
    assert item.id == item_id

    def mk_comparable(i: pystac.Item) -> Dict[str, Any]:
        i.common_metadata.created = None
        i.make_asset_hrefs_absolute()
        d = i.to_dict(include_self_link=False)

        if d["geometry"]["type"] == "Polygon":
            if len(d["geometry"]["coordinates"]) > 1:
                for i in range(0, len(d["geometry"]["coordinates"][0])):
                    for c in d["geometry"]["coordinates"][0][i]:
                        c[0] = round(c[0], COORD_ROUNDING)
                        c[1] = round(c[1], COORD_ROUNDING)
            else:
                for c in d["geometry"]["coordinates"][0]:
                    c[0] = round(c[0], COORD_ROUNDING)
                    c[1] = round(c[1], COORD_ROUNDING)

        for i, v in enumerate(bbox := d["bbox"]):
            bbox[i] = round(v, 5)

        return d

    assert item.common_metadata.created is not None

    assert mk_comparable(item) == mk_comparable(
        pystac.Item.from_file(f"{granule_href}/expected_output.json")
    )

    bands_seen = set()
    bands_to_assets = defaultdict(list)

    for key, asset in item.assets.items():
        # Ensure that there's no relative path parts
        # in the asset HREFs
        assert "/./" not in asset.href
        assert is_absolute_href(asset.href)
        asset_eo = EOExtension.ext(asset)
        bands = asset_eo.bands
        if bands is not None:
            bands_seen |= set(b.name for b in bands)
            if key.split("_")[0] in SENTINEL_BANDS:
                for b in bands:
                    bands_to_assets[b.name].append((key, asset))

    used_bands = dict(SENTINEL_BANDS)
    # if item.properties[f"{s2_prefix}:product_type"] == "S2MSI1C":
    #    used_bands = SENTINEL_BANDS
    if item.properties[f"{s2_prefix}:product_type"] == "S2MSI2A":
        used_bands.pop("cirrus")
        for b in chain(used_bands.keys(), ["visual", "aot", "wvp", "scl"]):
            assert b in item.assets

    assert bands_seen == set([b.name for k, b in used_bands.items()])

    # Check that multiple resolutions exist for assets that
    # have them, and that they are named such that the highest
    # resolution asset is the band name, and others are
    # appended with the resolution.

    resolutions_seen = defaultdict(list)

    # Level 1C does not have the same layout as Level 2A. So the
    # whole resolution
    if item.properties[f"{s2_prefix}:product_type"] == "S2MSI1C":
        for band_name, assets in bands_to_assets.items():
            for asset_key, asset in assets:
                resolutions_seen[band_name].append(asset.extra_fields["gsd"])

        # Level 1C only has the highest resolution version of each band
        used_resolutions = {
            band: [resolutions[0]] for band, resolutions in BANDS_TO_RESOLUTIONS.items()
        }
    elif item.properties[f"{s2_prefix}:product_type"] == "S2MSI2A":
        for band_name, assets in bands_to_assets.items():
            for asset_key, asset in assets:
                resolutions = BANDS_TO_RESOLUTIONS[band_name]

                asset_split = asset_key.split("_")
                assert len(asset_split) <= 2

                href_band = re.search(r"[_/](B\d[A\d])", asset.href).group(1)
                asset_res = extract_gsd(asset.href)
                assert href_band == band_name
                if len(asset_split) == 1:
                    assert asset_res == resolutions[0]
                    assert "gsd" in asset.extra_fields
                    resolutions_seen[band_name].append(asset_res)
                else:
                    assert asset_res != resolutions[0]
                    assert asset_res in resolutions
                    assert "gsd" not in asset.extra_fields
                    resolutions_seen[band_name].append(asset_res)

        # Level 2A does not have Band 10
        used_resolutions = dict(BANDS_TO_RESOLUTIONS)
        used_resolutions.pop("B10")

    assert set(resolutions_seen.keys()) == set(used_resolutions.keys())

    # self.assertLess(proj_bbox_area_difference(item), 0.005)

    mgrs = MgrsExtension.ext(item)
    assert f"_T{mgrs.utm_zone:02d}{mgrs.latitude_band}{mgrs.grid_square}" in item.id
    assert mgrs.latitude_band
    assert mgrs.utm_zone
    assert mgrs.grid_square

    grid = GridExtension.ext(item)
    assert grid.code
    grid_id = grid.code.split("-")[1]
    if len(grid_id) == 4:
        grid_id = f"0{grid_id}"  # add zero pad
    assert f"_T{grid_id}" in item.id

    try:
        view = ViewExtension.ext(item)
        assert view.sun_azimuth
        assert view.sun_elevation
    except pystac.errors.ExtensionNotImplemented as e:
        # this item is the example that doesn't have the View Extension
        # applied because the values are NaN
        if item_id != "S2A_T01WCP_20230625T234624_L2A":
            raise e

    proj = ProjectionExtension.ext(item)
    assert proj.centroid
    assert proj.centroid["lat"]
    assert proj.centroid["lon"]
