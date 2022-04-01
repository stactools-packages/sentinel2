from typing import List, Final, Pattern, Optional
import re

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
            x == '0' for i, x in enumerate(coord_values) if i % 3 == 2 and x
        ]

        if all(third_position_is_zero):
            # Assuming that all 3rd position coordinates are z values
            # Remove them.
            return [float(c) for i, c in enumerate(coord_values) if i % 3 != 2]

    return [float(c) for c in coord_values if c]
