import re
from typing import Final, List, Optional, Pattern

import shapely
from pystac import Item
from shapely.geometry import MultiPolygon, Polygon, shape
from stactools.core.utils import antimeridian
from stactools.core.utils.antimeridian import Strategy

GSD_PATTERN: Final[Pattern[str]] = re.compile(r"[_R](\d0)m")


def extract_gsd(image_path: str) -> Optional[int]:
    match = GSD_PATTERN.search(image_path)
    if match:
        return int(match.group(1))
    else:
        return None


def fix_z_values(coord_values: List[str]) -> List[float]:
    """Some geometries have a '0' value in the z position
    of the coordinates. This method detects and removes z
    position coordinates. This assumes that in cases where
    the z value is included, it is included for all coordinates.
    """
    if len(coord_values) % 3 == 0:
        # Check if all 3rd position values are '0'
        # Ignore any blank values
        third_position_is_zero = [
            x == "0" for i, x in enumerate(coord_values) if i % 3 == 2 and x
        ]

        if all(third_position_is_zero):
            # Assuming that all 3rd position coordinates are z values
            # Remove them.
            return [float(c) for i, c in enumerate(coord_values) if i % 3 != 2]

    return [float(c) for c in coord_values if c]


def handle_antimeridian(item: Item, antimeridian_strategy: Strategy) -> None:
    """Handles some quirks of the antimeridian.
    Applies the requested SPLIT or NORMALIZE strategy via the stactools
    antimeridian utility. If the geometry is already SPLIT (a MultiPolygon,
    which can occur when using USGS geometry), a merged polygon with different
    longitude signs is created to match the expected input of the fix_item
    function.
    Args:
        item (Item): STAC Item
        antimeridian_strategy (Antimeridian): Either split on +/-180 or
            normalize geometries so all longitudes are either positive or
            negative.
    """
    geometry = shape(item.geometry)
    if isinstance(geometry, MultiPolygon):
        # force all positive lons so we can merge on an antimeridian split
        polys = list(geometry.geoms)
        for index, poly in enumerate(polys):
            coords = list(poly.exterior.coords)
            lons = [coord[0] for coord in coords]
            if min(lons) < 0:
                polys[index] = shapely.affinity.translate(poly, xoff=+360)
        merged_geometry = shapely.ops.unary_union(polys)

        # revert back to + and - lon signs for fix_item's expected input
        merged_coords = list(merged_geometry.exterior.coords)
        for index, coord in enumerate(merged_coords):
            if coord[0] > 180:
                merged_coords[index] = (coord[0] - 360, coord[1])
        item.geometry = Polygon(merged_coords)

    antimeridian.fix_item(item, antimeridian_strategy)
