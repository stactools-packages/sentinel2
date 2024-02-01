import platform

import pytest
import shapely.geometry
from stactools.sentinel2 import stac

from . import test_data


def test_product_metadata_asset() -> None:
    file_name = "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ"
    path = test_data.get_path(f"data-files/{file_name}")
    item = stac.create_item(path)
    assert "product_metadata" in item.assets


def test_raises_for_missing_tileDataGeometry() -> None:
    file_name = (
        "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ-no-tileDataGeometry"
    )
    path = test_data.get_path(f"data-files/{file_name}")
    with pytest.raises(ValueError) as e:
        stac.create_item(path)
    assert "Metadata does not contain geometry" in str(e)


def test_raises_for_empty_geometry_coordinates() -> None:
    file_name = (
        "S2B_OPER_MSI_L2A_DS_VGS1_20201101T095401_S20201101T074429-no-data"  # noqa
    )
    path = test_data.get_path(f"data-files/{file_name}")
    with pytest.raises(ValueError) as e:
        stac.create_item(path)
    assert "with no coordinates" in str(e)


# this scene produces a correct geometry when running on arm64, but incorrect when
# running on amd64. This tests a check that the area of the geometry is larger than
# a correct one should be, that the creation of it fails, which is seen as better than
# outputting a bad geometry. Hopefully, we'll be able to figure out the underlying cause
# of this in the future
def test_raises_for_invalid_geometry_after_reprojection() -> None:
    file_name = "S2A_T60CWS_20240109T203651_L2A-pole-and-antimeridian-bad-geometry-after-reprojection"  # noqa
    path = test_data.get_path(f"data-files/{file_name}")
    if platform.machine() == "arm64":
        stac.create_item(path)
    elif platform.machine() == "x86_64":
        with pytest.raises(Exception) as e:
            stac.create_item(path)
        assert "Area of geometry is " in str(e)
    else:
        pytest.fail(f"unknown platform.machine '{platform.machine()}'")


# this scene creates a geometry that's globe-spanning, so it should throw an exception
def test_raises_for_invalid_geometry() -> None:
    file_name = "S2A_OPER_MSI_L2A_DS_2APS_20230105T201055_S20230105T163809"  # noqa
    path = test_data.get_path(f"data-files/{file_name}")
    if platform.machine() == "arm64":
        with pytest.raises(Exception) as e:
            stac.create_item(path)
        assert "Area of geometry is " in str(e)
    elif platform.machine() == "x86_64":
        # fails in antimeridian on "assert not interiors"
        with pytest.raises(AssertionError) as e:
            stac.create_item(path)
    else:
        pytest.fail(f"unknown platform.machine '{platform.machine()}'")


def test_antimeridian() -> None:
    path = test_data.get_path(
        "data-files/S2A_MSIL2A_20230821T221941_N0509_R029_T01KAB_20230822T021825.SAFE"
    )
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
