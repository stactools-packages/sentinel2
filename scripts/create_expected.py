#!/usr/bin/env python3

from pathlib import Path

from stactools.sentinel2 import stac

EXCLUDE = [
    "S2A_T60CWS_20240109T203651_L2A-pole-and-antimeridian-bad-geometry-after-reprojection",
    "S2B_OPER_MSI_L2A_DS_VGS1_20201101T095401_S20201101T074429-no-data",
    "S2A_OPER_MSI_L2A_DS_2APS_20230105T201055_S20230105T163809",
    "S2A_MSIL2A_20150826T185436_N0212_R070_T11SLT_20210412T023147",
    "S2A_MSIL2A_20180721T053721_N0212_R062_T43MDV_20201011T181419.SAFE",
    "S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857",
    "S2A_MSIL1C_20210908T042701_N0301_R133_T46RER_20210908T070248",
    "S2B_MSIL2A_20191228T210519_N0212_R071_T01CCV_20201003T104658",
    "S2A_OPER_MSI_L2A_TL_VGS1_20220401T110010_A035382_T34LBQ-no-tileDataGeometry",
]

root = Path(__file__).parents[1]
data_files = root / "tests" / "data-files"

errored = False
for path in data_files.iterdir():
    if path.name in EXCLUDE or path.name.startswith("."):
        continue
    print(path)
    try:
        item = stac.create_item(str(path))
        item.set_self_href(str(data_files / path.name / "expected_output.json"))
        item.make_asset_hrefs_relative()
        item.validate()
        item.save_object(include_self_link=False)

    except Exception as e:
        print(e)
        errored = True

if errored:
    print("At least one error occurred")
    exit(1)
