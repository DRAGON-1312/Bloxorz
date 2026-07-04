from dataclasses import dataclass
from enum import Enum


class Orientation(Enum):
    STANDING = "standing"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class BlockMode(Enum):
    NORMAL = "normal"
    SPLIT = "split"


@dataclass(frozen=True)
class State:
    # NORMAL mode fields
    row: int
    col: int
    orientation: Orientation

    # Shared fields
    bridges: tuple = ()

    # SPLIT mode fields
    mode: BlockMode = BlockMode.NORMAL
    cube1: tuple[int, int] | None = None
    cube2: tuple[int, int] | None = None
    active_cube: int = 1