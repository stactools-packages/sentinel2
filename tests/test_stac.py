from stactools.sentinel2 import stac

from . import test_data


def test_product_metadata_asset() -> None:
    file_name = "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ"
    path = test_data.get_path(f"data-files/{file_name}")
    item = stac.create_item(path)
    assert "product_metadata" in item.assets
