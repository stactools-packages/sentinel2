#!/usr/bin/env python3

import datetime
import shutil
import warnings
from pathlib import Path

from antimeridian import FixWindingWarning
from pystac import (
    Catalog,
    CatalogType,
    Collection,
    Extent,
    SpatialExtent,
    TemporalExtent,
)

from stactools.sentinel2.stac import create_item

DEFAULT_EXTENT = Extent(
    SpatialExtent([[-180, -90, 180, 90]]),
    TemporalExtent([[datetime.datetime.utcnow(), None]]),
)

root = Path(__file__).parents[1]
examples = root / "examples"
data_files = root / "tests" / "data-files"

if examples.exists():
    shutil.rmtree(examples)
examples.mkdir()

catalog = Catalog(
    id="sentinel2-examples",
    description="Example collections and items for stactools-sentinel2",
)

l1c_collection = Collection(
    id="sentinel2-l1c-example",
    description="Example collection of sentinel2 L1C data",
    extent=DEFAULT_EXTENT,
)
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FixWindingWarning)
    l1c_item = create_item(
        str(data_files / "S2A_MSIL1C_20200717T221941_R029_T01LAC_20200717T234135.SAFE")
    )
l1c_collection.add_item(l1c_item)
l1c_collection.update_extent_from_items()

l2a_collection = Collection(
    id="sentinel2-l2a-example",
    description="Example collection of sentinel2 L1C data",
    extent=DEFAULT_EXTENT,
)
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FixWindingWarning)
    l2a_item = create_item(
        str(
            data_files
            / "S2A_MSIL2A_20190212T192651_N0212_R013_T07HFE_20201007T160857.SAFE"
        )
    )
l2a_collection.add_item(l2a_item)
l2a_collection.update_extent_from_items()

catalog.add_children([l1c_collection, l2a_collection])
catalog.normalize_hrefs(str(examples))
catalog.make_all_asset_hrefs_relative()
catalog.save(CatalogType.SELF_CONTAINED)
