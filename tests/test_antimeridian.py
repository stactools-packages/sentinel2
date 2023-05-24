import unittest
from typing import Any, List

from stactools.core.utils.antimeridian import Strategy

from stactools.sentinel2 import stac
from tests import test_data


def recursive_round(coordinates: List[Any], precision: int) -> List[Any]:
    rounded: List[Any] = []
    for value in coordinates:
        if isinstance(value, (int, float)):
            rounded.append(round(value, precision))
        else:
            rounded.append(recursive_round(list(value), precision))
    return rounded


class Sentinel2AntimeridianTest(unittest.TestCase):

    def test_split(self):
        href = test_data.get_path(
            "data-files/S2B_MSIL2A_20230122T231849_N0400_R087_T01UBT_20230124T042703.SAFE"  # noqa
        )
        item = stac.create_item(href, antimeridian_strategy=Strategy.SPLIT)
        produced = item.geometry
        expected = {
            "type":
            "MultiPolygon",
            "coordinates": [
                [[
                    [-180.0, 52.311126487159584],
                    [-180.0, 51.32330761850015],
                    [-179.96284, 51.32442493525441],
                    [-179.92305, 51.402000025022936],
                    [-179.84846, 51.54604362003081],
                    [-179.77333, 51.69005105235231],
                    [-179.75468, 51.72545617073585],
                    [-179.79091, 52.31749831400855],
                    [-180.0, 52.311126487159584],
                ]],
                [[
                    [180.0, 51.32330761850015],
                    [180.0, 52.311126487159584],
                    [178.6023109540294, 52.268533459479656],
                    [178.6971513291282, 51.28413502651741],
                    [180.0, 51.32330761850015],
                ]],
            ],
        }
        self.assertEqual(produced["type"], "MultiPolygon")
        rounded_produced = recursive_round(produced["coordinates"], 5)
        rounded_expected = recursive_round(expected["coordinates"], 5)
        self.assertEqual(rounded_expected, rounded_produced)

    def test_normalize(self):
        href = test_data.get_path(
            "data-files/S2B_MSIL2A_20230122T231849_N0400_R087_T01UBT_20230124T042703.SAFE"  # noqa
        )
        item = stac.create_item(href, antimeridian_strategy=Strategy.NORMALIZE)
        produced = item.geometry
        expected = {
            "type":
            "Polygon",
            "coordinates": [[
                [180.0, 51.32330761850015],
                [180.03716, 51.32442493525441],
                [180.07695, 51.402000025022936],
                [180.15154, 51.54604362003081],
                [180.22667, 51.69005105235231],
                [180.24532, 51.72545617073585],
                [180.20909, 52.31749831400855],
                [180.0, 52.311126487159584],
                [178.6023109540294, 52.268533459479656],
                [178.6971513291282, 51.28413502651741],
                [180.0, 51.32330761850015],
            ]],
        }
        self.assertEqual(produced["type"], "Polygon")
        rounded_produced = recursive_round(produced["coordinates"], 5)
        rounded_expected = recursive_round(expected["coordinates"], 5)
        self.assertEqual(rounded_expected, rounded_produced)
