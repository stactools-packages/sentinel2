import pytest
import shapely.geometry
from antimeridian import FixWindingWarning
from stactools.sentinel2 import stac

from . import test_data


def test_product_metadata_asset() -> None:
    file_name = "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ"
    path = test_data.get_path(f"data-files/{file_name}")
    with pytest.warns(FixWindingWarning):
        item = stac.create_item(path)
    assert "product_metadata" in item.assets


def test_antimeridian() -> None:
    path = test_data.get_path(
        "data-files/S2A_MSIL2A_20230821T221941_N0509_R029_T01KAB_20230822T021825.SAFE"
    )
    with pytest.warns(FixWindingWarning):
        item = stac.create_item(path)
    expected = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [180.0, -16.259071],
                    [180.0, -16.259071],
                    [179.258625, -16.247763],
                    [179.23921, -17.238192],
                    [180.0, -17.250482],
                    [180.0, -17.250482],
                    [180.0, -16.259071],
                ]
            ],
            [
                [
                    [-180.0, -17.250482],
                    [-179.72957, -17.25485],
                    [-179.71545, -16.263411],
                    [-180.0, -16.259071],
                    [-180.0, -17.250482],
                ]
            ],
        ],
    }
    assert (
        shapely.geometry.shape(expected)
        .normalize()
        .equals_exact(shapely.geometry.shape(item.geometry).normalize(), tolerance=5)
    )
