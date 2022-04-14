import os
import re
from collections import defaultdict
from itertools import chain
from tempfile import TemporaryDirectory
from typing import Dict, Final, List

import pystac
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
from pystac.utils import is_absolute_href
from shapely.geometry import box, mapping, shape
from stactools.core.projection import reproject_geom
from stactools.testing import CliTestCase

from stactools.sentinel2.commands import create_sentinel2_command
from stactools.sentinel2.constants import BANDS_TO_ASSET_NAME
from stactools.sentinel2.constants import SENTINEL2_PROPERTY_PREFIX as s2_prefix
from stactools.sentinel2.constants import SENTINEL_BANDS
from stactools.sentinel2.grid import GridExtension
from stactools.sentinel2.mgrs import MgrsExtension
from stactools.sentinel2.utils import extract_gsd
from tests import test_data

BANDS_TO_RESOLUTIONS: Final[Dict[str, List[int]]] = {
    "coastal": [
        60,
        20,
    ],  # asset coastal is 60, coastal_20m is 20, as 20m wasn't added until 2021/22
    "blue": [10, 20, 60],
    "green": [10, 20, 60],
    "red": [10, 20, 60],
    "rededge1": [20, 60],
    "rededge2": [20, 60],
    "rededge3": [20, 60],
    "nir": [10, 20, 60],
    "nir08": [20, 60],
    "nir09": [60],
    "cirrus": [60],
    "swir16": [20, 60],
    "swir22": [20, 60],
}


def proj_bbox_area_difference(item):
    projection = ProjectionExtension.ext(item)
    visual_asset = item.assets.get("visual_10m") or item.assets.get("visual")
    asset_projection = ProjectionExtension.ext(visual_asset)
    pb = mapping(box(*asset_projection.bbox))
    proj_geom = shape(reproject_geom(f"epsg:{projection.epsg}", "epsg:4326", pb))

    item_geom = shape(item.geometry)

    difference_area = item_geom.difference(proj_geom).area
    raster_area = proj_geom.area

    # We expect the footprint to be in the raster
    # bounds, so any difference should be relatively very low
    # and due to reprojection.
    return difference_area / raster_area


class CreateItemTest(CliTestCase):
    def create_subcommand_functions(self):
        return [create_sentinel2_command]

    def test_create_item(self):
        # fmt: off
        id_to_filename = {
            "S2A_MSIL1C_20210908T042701_R133_T46RER_20210908T070248":
                "S2A_MSIL1C_20210908T042701_N0301_R133_T46RER_20210908T070248.SAFE",
            "S2A_MSIL2A_20190212T192651_R013_T07HFE_20201007T160857":
                "S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE",
            "S2B_MSIL2A_20191228T210519_R071_T01CCV_20201003T104658":
                "S2B_MSIL2A_20191228T210519_N0212_R071_T01CCV_20201003T104658.SAFE",
            "S2B_MSIL2A_20210122T133229_R081_T22HBD_20210122T155500":
                "esa_S2B_MSIL2A_20210122T133229_N0214_R081_T22HBD_20210122T155500.SAFE",
            "S2A_OPER_MSI_L2A_TL_SGS__20181231T210250_A018414_T10SDG":
                "S2A_OPER_MSI_L2A_TL_SGS__20181231T210250_A018414_T10SDG",
            "S2A_OPER_MSI_L1C_TL_SGS__20181231T203637_A018414_T10SDG":
                "S2A_OPER_MSI_L1C_TL_SGS__20181231T203637_A018414_T10SDG",
            "S2B_MSIL2A_20220413T150759_R025_T33XWJ_20220414T082126":
                "S2B_MSIL2A_20220413T150759_N0400_R025_T33XWJ_20220414T082126.SAFE",
        }
        # fmt: on

        granule_hrefs = {
            k: test_data.get_path(f"data-files/{v}")
            for (k, v) in id_to_filename.items()
        }

        for item_id, granule_href in granule_hrefs.items():
            with self.subTest(granule_href):
                with TemporaryDirectory() as tmp_dir:
                    cmd = ["sentinel2", "create-item", granule_href, tmp_dir]
                    self.run_command(cmd)  # type: ignore

                    jsons = [p for p in os.listdir(tmp_dir) if p.endswith(".json")]
                    self.assertEqual(len(jsons), 1)
                    fname = jsons[0]

                    item = pystac.Item.from_file(os.path.join(tmp_dir, fname))

                    item.validate()

                    self.assertEqual(item.id, item_id)

                    assert item.to_dict(
                        include_self_link=False
                    ) == pystac.Item.from_file(
                        f"{granule_href}/expected_output.json"
                    ).to_dict(
                        include_self_link=False
                    )

                    bands_seen = set()
                    bands_to_assets = defaultdict(list)

                    for key, asset in item.assets.items():
                        # Ensure that there's no relative path parts
                        # in the asset HREFs
                        self.assertTrue("/./" not in asset.href)

                        self.assertTrue(is_absolute_href(asset.href))
                        asset_eo = EOExtension.ext(asset)
                        bands = asset_eo.bands
                        if bands is not None:
                            bands_seen |= set(b.name for b in bands)
                            if key.split("_")[0] in SENTINEL_BANDS:
                                for b in bands:
                                    bands_to_assets[b.name].append((key, asset))

                    if item.properties[f"{s2_prefix}:product_type"] == "S2MSI1C":
                        used_bands = SENTINEL_BANDS
                    elif item.properties[f"{s2_prefix}:product_type"] == "S2MSI2A":
                        used_bands = dict(SENTINEL_BANDS)
                        used_bands.pop("cirrus")
                        for b in chain(
                            used_bands.keys(), ["visual", "aot", "wvp", "scl"]
                        ):
                            self.assertIn(b, item.assets.keys())

                    self.assertEqual(bands_seen, set(used_bands.keys()))

                    # Check that multiple resolutions exist for assets that
                    # have them, and that they are named such that the highest
                    # resolution asset is the band name, and others are
                    # appended with the resolution.

                    resolutions_seen = defaultdict(list)

                    # Level 1C does not have the same layout as Level 2A. So the
                    # whole resolution
                    if item.properties[f"{s2_prefix}:product_type"] == "S2MSI1C":
                        for band_name, assets in bands_to_assets.items():
                            for (asset_key, asset) in assets:
                                resolutions_seen[band_name].append(
                                    asset.extra_fields["gsd"]
                                )

                        # Level 1C only has the highest resolution version of each band
                        used_resolutions = {
                            band: [resolutions[0]]
                            for band, resolutions in BANDS_TO_RESOLUTIONS.items()
                        }
                    elif item.properties[f"{s2_prefix}:product_type"] == "S2MSI2A":
                        for band_name, assets in bands_to_assets.items():
                            for (asset_key, asset) in assets:
                                resolutions = BANDS_TO_RESOLUTIONS[band_name]

                                asset_split = asset_key.split("_")
                                self.assertLessEqual(len(asset_split), 2)

                                href_band = re.search(
                                    r"[_/](B\d[A\d])", asset.href
                                ).group(1)
                                asset_res = extract_gsd(asset.href)
                                self.assertEqual(
                                    BANDS_TO_ASSET_NAME[href_band], band_name
                                )
                                if len(asset_split) == 1:
                                    self.assertEqual(asset_res, resolutions[0])
                                    self.assertIn("gsd", asset.extra_fields)
                                    resolutions_seen[band_name].append(asset_res)
                                else:
                                    self.assertNotEqual(asset_res, resolutions[0])
                                    self.assertIn(asset_res, resolutions)
                                    self.assertNotIn("gsd", asset.extra_fields)
                                    resolutions_seen[band_name].append(asset_res)

                        # Level 2A does not have Band 10
                        used_resolutions = dict(BANDS_TO_RESOLUTIONS)
                        used_resolutions.pop("cirrus")

                    self.assertEqual(
                        set(resolutions_seen.keys()), set(used_resolutions.keys())
                    )
                    for band in resolutions_seen:
                        # B08 (nir) has only 10m resolution in SAFE archive
                        # but 20m and 60m in S3 sinergise data
                        # B01 (coastal) has 60m data for all years,
                        # but also 20m for 2021/22 and newer.
                        if band == "nir" or band == "coastal":
                            if len(resolutions_seen[band]) == 1:
                                self.assertEqual(
                                    set(resolutions_seen[band]),
                                    {used_resolutions[band][0]},
                                )
                            else:
                                self.assertEqual(
                                    set(resolutions_seen[band]),
                                    set(used_resolutions[band]),
                                )
                        else:
                            self.assertEqual(
                                set(resolutions_seen[band]), set(used_resolutions[band])
                            )

                    self.assertLess(proj_bbox_area_difference(item), 0.005)

                    self.assertTrue(item.properties.get("mgrs:latitude_band"))
                    self.assertTrue(item.properties.get("mgrs:utm_zone"))
                    self.assertTrue(item.properties.get("mgrs:grid_square"))

                    mgrs = MgrsExtension.ext(item)
                    self.assertIn(
                        f"_T{mgrs.utm_zone:02d}{mgrs.latitude_band}{mgrs.grid_square}",
                        item.id,
                    )

                    self.assertTrue(item.properties.get("grid:code"))

                    grid = GridExtension.ext(item)
                    grid_id = grid.code.split("-")[1]
                    if len(grid_id) == 4:
                        grid_id = f"0{grid_id}"  # add zero pad
                    self.assertIn(f"_T{grid_id}", item.id)

                    self.assertTrue(item.properties.get("view:sun_azimuth"))
                    self.assertTrue(item.properties.get("view:sun_elevation"))
                    view = ViewExtension.ext(item)
                    self.assertTrue(view.sun_azimuth)
                    self.assertTrue(view.sun_elevation)
