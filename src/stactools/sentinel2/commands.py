import json
import logging
import os
from typing import Optional

import click
from pystac import CatalogType
from stactools.core.utils.antimeridian import Strategy

from stactools.sentinel2.constants import DEFAULT_TOLERANCE
from stactools.sentinel2.stac import create_collection, create_item

logger = logging.getLogger(__name__)


def create_sentinel2_command(cli):
    @cli.group("sentinel2", short_help="Commands for working with sentinel2 data")
    def sentinel2():
        pass

    @sentinel2.command(
        "create-item", short_help="Convert a Sentinel2 L2A granule into a STAC item"
    )
    @click.argument("src")
    @click.argument("dst")
    @click.option(
        "-p",
        "--providers",
        help="Path to JSON file containing array of additional providers",
    )
    @click.option(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="Item geometry simplification tolerance, e.g., 0.0001",
    )
    @click.option(
        "--asset-href-prefix",
        help='Prefix for all Asset hrefs instead of default of the "src" value',
    )
    def create_item_command(
        src: str,
        dst: str,
        providers: Optional[str],
        tolerance: float,
        asset_href_prefix: Optional[str],
    ):
        """Creates a STAC Item for a given Sentinel 2 granule

        SRC is the path to the granule
        DST is directory that a STAC Item JSON file will be created
        in. This will have a filename that matches the ID, which will
        be derived from the Sentinel 2 metadata.
        """
        additional_providers = None
        if providers is not None:
            with open(providers) as f:
                additional_providers = json.load(f)

        antimeridian_strategy = "split"
        strategy = Strategy[antimeridian_strategy.upper()]
        item = create_item(
            granule_href=src,
            additional_providers=additional_providers,
            tolerance=tolerance,
            asset_href_prefix=asset_href_prefix,
            antimeridian_strategy=strategy,
        )

        item_path = os.path.join(dst, "{}.json".format(item.id))
        item.set_self_href(item_path)

        item.save_object()

    # return sentinel2

    @sentinel2.command(
        "create-collection",
        short_help="Creates a STAC Collection with contents defined by a list "
        " of metadata file hrefs in a text file.",
    )
    @click.option(
        "-f",
        "--file_list",
        required=True,
        help="Text file of HREFs to Landsat scene XML MTL metadata " "files.",
    )
    @click.option(
        "-o",
        "--output",
        required=True,
        help="HREF of directory in which to write the collection.",
    )
    @click.option(
        "-i",
        "--id",
        type=click.Choice(
            ["sentinel2-c1-l1c", "sentinel2-c2-l2a"], case_sensitive=True
        ),
        required=True,
        help="Sentinel2 collection type. Choice of 'sentinel2-c1-l1c' "
        "'sentinel2-c2-l2a'",
    )
    @click.option(
        "-a",
        "--antimeridian_strategy",
        type=click.Choice(["normalize", "split"], case_sensitive=False),
        default="split",
        show_default=True,
        help="geometry strategy for antimeridian scenes",
    )
    def create_collection_cmd(
        file_list: str,
        output: str,
        id: str,
        antimeridian_strategy: str,
    ) -> None:
        """Creates a STAC Collection for Items defined by the hrefs in file_list.
        Args:
            file_list (str): Text file containing one href per line. The hrefs
                should point to XML MTL metadata files.
            output (str): Directory that will contain the collection.
            id (str): Choice of 'landsat-c2-l1' or 'landsat-c2-l2'.
            antimeridian_strategy (str): Choice of 'normalize' or 'split' to
                either split the Item geometry on -180 longitude or normalize
                the Item geometry so all longitudes are either positive or
                negative.
        """
        strategy = Strategy[antimeridian_strategy.upper()]
        with open(file_list) as file:
            hrefs = [line.strip() for line in file.readlines()]

        collection = create_collection(id)
        collection.set_self_href(os.path.join(output, "collection.json"))
        collection.catalog_type = CatalogType.SELF_CONTAINED
        for href in hrefs:
            item = create_item(
                href,
                antimeridian_strategy=strategy,
            )
            collection.add_item(item)
        # collection.make_all_asset_hrefs_relative()
        collection.validate_all()
        collection.save()

        return sentinel2
