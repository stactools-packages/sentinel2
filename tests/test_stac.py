import pytest
import shapely.geometry

from stactools.sentinel2 import stac

from . import test_data


def test_product_metadata_asset() -> None:
    file_name = "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ"
    path = test_data.get_path(f"data-files/{file_name}")
    item = stac.create_item(path)
    assert "product_metadata" in item.assets


# this scene has one vertex that just crosses the antimeridian
# but is snapped to the antimeridian line
def test_one_vertex_just_crossing() -> None:
    file_name = "S2B_MSIL2A_20200914T231559_N0500_R087_T01VCG_20230315T224658"  # noqa
    path = test_data.get_path(f"data-files/{file_name}")
    stac.create_item(path)


# this scene previously produced a correct geometry when running on arm64, but incorrect
# large globe-spanning geometry on amd64. This checks for regression.
def test_polar_antimeridian_crossing() -> None:
    file_name = "S2A_T60CWS_20240109T203651_L2A"  # noqa
    path = test_data.get_path(f"data-files/{file_name}")
    stac.create_item(path)


# this scene previously created a geometry that's globe-spanning
# checks for regression
def test_antimeridian_crossing() -> None:
    file_name = "S2A_OPER_MSI_L2A_DS_2APS_20230105T201055_S20230105T163809"  # noqa
    path = test_data.get_path(f"data-files/{file_name}")
    stac.create_item(path)


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
                    [179.258625, -16.247763],
                    [179.23921, -17.238192],
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


def test_make_geometry_collection_filter():
    input_geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70, 6],
                [-74, 6],
                [-74, 6.5],  #
                [-72, 6.5],  # will result in a linestring
                [-74, 6.5],  #
                [-74, 7],
                [-70, 7],
                [-70, 6],
            ]
        ],
    }

    expected = {
        "type": "Polygon",
        "coordinates": [[[-74, 7], [-70, 7], [-70, 6], [-74, 6], [-74, 6.5], [-74, 7]]],
    }
    valid_geometry = stac.make_valid_geometry(input_geometry)

    assert (
        shapely.geometry.shape(expected)
        .normalize()
        .equals_exact(valid_geometry.normalize(), tolerance=5)
    )


def test_deduplicate_points():
    input_geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70, 6],
                [-74, 6],
                [-74, 6.5],
                [-74, 6.5],  # Duplicated
                [-74, 7],
                [-70, 7],
                [-70, 6],
            ]
        ],
    }

    expected = {
        "type": "Polygon",
        "coordinates": [[[-74, 7], [-70, 7], [-70, 6], [-74, 6], [-74, 6.5], [-74, 7]]],
    }
    valid_geometry = stac.make_valid_geometry(input_geometry)

    assert (
        shapely.geometry.shape(expected)
        .normalize()
        .equals_exact(valid_geometry.normalize(), tolerance=5)
    )


def test_fallback_geometry():
    file_name = (
        "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ-no-tileDataGeometry"  # noqa
    )
    path = test_data.get_path(f"data-files/{file_name}")
    stac.create_item(path)


@pytest.mark.parametrize(
    ("file_name", "allow_fallback_geometry"),
    [
        [
            "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ-no-tileDataGeometry",
            False,
        ],  # Raise if no tileDataGeometry and not allowed to fallback
        [
            "S2B_OPER_MSI_L2A_DS_VGS1_20201101T095401_S20201101T074429-no-data",
            False,
        ],  # Raise if no coords in tileDataGeometry and not allowed to fallback
        [
            "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ-no-tileDataGeometry-no-product-metadata",
            True,
        ],  # Raise if no tileDataGeometry and no product metadata
    ],
)
def test_fallback_geometry_raises(file_name, allow_fallback_geometry):
    path = test_data.get_path(f"data-files/{file_name}")
    with pytest.raises(ValueError) as e:
        stac.create_item(path, allow_fallback_geometry=allow_fallback_geometry)
    assert "Metadata does not contain geometry" in str(e)
