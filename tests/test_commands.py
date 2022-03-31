from collections import defaultdict
import os
from tempfile import TemporaryDirectory
from stactools.sentinel2.mgrs import MgrsExtension
from stactools.sentinel2.grid import GridExtension

import pystac
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.utils import is_absolute_href
from shapely.geometry import box, shape, mapping

from stactools.core.projection import reproject_geom
from stactools.sentinel2.commands import create_sentinel2_command
from stactools.sentinel2.constants import BANDS_TO_RESOLUTIONS, SENTINEL_BANDS
from stactools.testing import CliTestCase

from tests import test_data


class CreateItemTest(CliTestCase):

    def create_subcommand_functions(self):
        return [create_sentinel2_command]

    def test_create_item(self):
        granule_hrefs = {
            k: test_data.get_path(f'data-files/{v}')
            for (k, v) in
            [('S2A_MSIL1C_20210908T042701_R133_T46RER_20210908T070248',
              'S2A_MSIL1C_20210908T042701_N0301_R133_T46RER_20210908T070248.SAFE'
              ),
             ('S2A_MSIL2A_20190212T192651_R013_T07HFE_20201007T160857',
              'S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE'
              ),
             ('S2B_MSIL2A_20191228T210519_R071_T01CCV_20201003T104658',
              'S2B_MSIL2A_20191228T210519_N0212_R071_T01CCV_20201003T104658.SAFE'
              ),
             ('S2B_MSIL2A_20210122T133229_R081_T22HBD_20210122T155500',
              'esa_S2B_MSIL2A_20210122T133229_N0214_R081_T22HBD_20210122T155500.SAFE'
              )]
        }

        def check_proj_bbox(item):
            projection = ProjectionExtension.ext(item)
            visual_asset = item.assets.get('visual-10m') or \
                           item.assets.get('visual')
            asset_projection = ProjectionExtension.ext(visual_asset)
            pb = mapping(box(*asset_projection.bbox))
            proj_geom = shape(
                reproject_geom(f'epsg:{projection.epsg}', 'epsg:4326', pb))

            item_geom = shape(item.geometry)

            difference_area = item_geom.difference(proj_geom).area
            raster_area = proj_geom.area

            # We expect the footprint to be in the raster
            # bounds, so any difference should be relatively very low
            # and due to reprojection.
            self.assertLess(difference_area / raster_area, 0.005)

        for item_id, granule_href in granule_hrefs.items():
            with self.subTest(granule_href):
                with TemporaryDirectory() as tmp_dir:
                    cmd = ['sentinel2', 'create-item', granule_href, tmp_dir]
                    self.run_command(cmd)  # type: ignore

                    jsons = [
                        p for p in os.listdir(tmp_dir) if p.endswith('.json')
                    ]
                    self.assertEqual(len(jsons), 1)
                    fname = jsons[0]

                    item = pystac.Item.from_file(os.path.join(tmp_dir, fname))

                    item.validate()

                    self.assertEqual(item.id, item_id)

                    bands_seen = set()
                    bands_to_assets = defaultdict(list)

                    for key, asset in item.assets.items():
                        # Ensure that there's no relative path parts
                        # in the asset HREFs
                        self.assertTrue('/./' not in asset.href)

                        self.assertTrue(is_absolute_href(asset.href))
                        asset_eo = EOExtension.ext(asset)
                        bands = asset_eo.bands
                        if bands is not None:
                            bands_seen |= set(b.name for b in bands)
                            if key.split('_')[0] in SENTINEL_BANDS:
                                for b in bands:
                                    bands_to_assets[b.name].append(
                                        (key, asset))

                    if item.properties['s2:product_type'] == 'S2MSI1C':
                        used_bands = SENTINEL_BANDS
                    elif item.properties['s2:product_type'] == 'S2MSI2A':
                        used_bands = dict(SENTINEL_BANDS)
                        used_bands.pop('B10')

                    self.assertEqual(bands_seen, set(used_bands.keys()))

                    # Check that multiple resolutions exist for assets that
                    # have them, and that they are named such that the highest
                    # resolution asset is the band name, and others are
                    # appended with the resolution.

                    resolutions_seen = defaultdict(list)

                    # Level 1C does not have the same layout as Level 2A. So the
                    # whole resolution
                    if item.properties['s2:product_type'] == 'S2MSI1C':
                        for band_name, assets in bands_to_assets.items():
                            for (asset_key, asset) in assets:
                                resolutions_seen[band_name].append(
                                    asset.extra_fields['gsd'])

                        # Level 1C only has highest resolution version of each band
                        used_resolutions = {
                            band: [resolutions[0]]
                            for band, resolutions in
                            BANDS_TO_RESOLUTIONS.items()
                        }
                    elif item.properties['s2:product_type'] == 'S2MSI2A':
                        for band_name, assets in bands_to_assets.items():
                            for (asset_key, asset) in assets:
                                resolutions = BANDS_TO_RESOLUTIONS[band_name]

                                asset_split = asset_key.split('_')
                                self.assertLessEqual(len(asset_split), 2)

                                href_band, href_res = os.path.splitext(
                                    asset.href)[0].split('_')[-2:]
                                asset_res = int(href_res.replace('m', ''))
                                self.assertEqual(href_band, band_name)
                                if len(asset_split) == 1:
                                    self.assertEqual(asset_res, resolutions[0])
                                    self.assertIn('gsd', asset.extra_fields)
                                    resolutions_seen[band_name].append(
                                        asset_res)
                                else:
                                    self.assertNotEqual(
                                        asset_res, resolutions[0])
                                    self.assertIn(asset_res, resolutions)
                                    self.assertNotIn('gsd', asset.extra_fields)
                                    resolutions_seen[band_name].append(
                                        asset_res)

                        # Level 2A does not have Band 10
                        used_resolutions = dict(BANDS_TO_RESOLUTIONS)
                        used_resolutions.pop('B10')

                    self.assertEqual(set(resolutions_seen.keys()),
                                     set(used_resolutions.keys()))
                    for band in resolutions_seen:
                        self.assertEqual(set(resolutions_seen[band]),
                                         set(used_resolutions[band]))

                    check_proj_bbox(item)

                    self.assertTrue(item.properties.get("mgrs:latitude_band"))
                    self.assertTrue(item.properties.get("mgrs:utm_zone"))
                    self.assertTrue(item.properties.get("mgrs:grid_square"))

                    mgrs = MgrsExtension.ext(item)
                    self.assertIn(
                        f"_T{mgrs.utm_zone:02d}{mgrs.latitude_band}{mgrs.grid_square}_",
                        item.id)

                    self.assertTrue(item.properties.get("grid:code"))

                    grid = GridExtension.ext(item)
                    grid_id = grid.code.split('-')[1]
                    if len(grid_id) == 4:
                        grid_id = f"0{grid_id}"  # add zero pad
                    self.assertIn(f"_T{grid_id}_", item.id)
