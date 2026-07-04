from enum import Enum 

class TileType(Enum):
    VOID = "void"                   # empty cell / empty space (Ô trống / khoảng không)
    FLOOR = "floor"                 # Normal floor tile
    GOAL = "goal"                   # Goal hole
    FRAGILE = "fragile"
    BRIDGE = "bridge"
    SOFT_SWITCH = "soft_switch"
    HEAVY_SWITCH = "heavy_switch"
    SPLIT_SWITCH = "split_switch"