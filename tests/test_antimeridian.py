import unittest

from stactools.core.utils.antimeridian import Strategy

from stactools.sentinel2 import stac
from tests import test_data


class Sentinel2AntimeridianTest(unittest.TestCase):

    def test_split(self):
        href = test_data.get_path(
            "data-files/S2B_MSIL2A_20230122T231849_N0400_R087_T01UBT_20230124T042703.SAFE"  # noqa
        )
        item = stac.create_item(href,
                                antimeridian_strategy=Strategy.SPLIT,
                                coordinate_precision=7)
        produced = item.geometry
        expected = {
            "type":
            "MultiPolygon",
            "coordinates": [
                [[
                    [-180.0, 52.3111265],
                    [-180.0, 51.3233076],
                    [-179.96284, 51.3244249],
                    [-179.92305, 51.402],
                    [-179.84846, 51.5460436],
                    [-179.77333, 51.6900511],
                    [-179.75468, 51.7254562],
                    [-179.79091, 52.3174983],
                    [-180.0, 52.3111265],
                ]],
                [[
                    [180.0, 51.3233076],
                    [180.0, 52.3111265],
                    [178.602311, 52.2685335],
                    [178.6971513, 51.284135],
                    [180.0, 51.3233076],
                ]],
            ],
        }
        self.assertEqual(produced["type"], "MultiPolygon")
        self.assertEqual(expected, produced)

    def test_normalize(self):
        href = test_data.get_path(
            "data-files/S2B_MSIL2A_20230122T231849_N0400_R087_T01UBT_20230124T042703.SAFE"  # noqa
        )
        item = stac.create_item(href,
                                antimeridian_strategy=Strategy.NORMALIZE,
                                coordinate_precision=7)
        produced = item.geometry
        expected = {
            "type":
            "Polygon",
            "coordinates": [[
                [180.0, 51.3233076],
                [180.03716, 51.3244249],
                [180.07695, 51.402],
                [180.15154, 51.5460436],
                [180.22667, 51.6900511],
                [180.24532, 51.7254562],
                [180.20909, 52.3174983],
                [180.0, 52.3111265],
                [178.602311, 52.2685335],
                [178.6971513, 51.284135],
                [180.0, 51.3233076],
            ]],
        }
        self.assertEqual(produced["type"], "Polygon")
        self.assertEqual(expected, produced)
