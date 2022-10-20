import json
import logging
import os
from typing import Optional

import click
from stactools.core.utils.antimeridian import Strategy

from stactools.sentinel2.constants import DEFAULT_TOLERANCE
from stactools.sentinel2.stac import create_item

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

    return sentinel2
