import json
from core.board import Board
from core.tiles import TileType


CHAR_TO_TILE = {
    "#": TileType.FLOOR, 
    ".": TileType.VOID,
    "S": TileType.FLOOR,    # Start tile
    "G": TileType.GOAL,     # Goal tile
    "F": TileType.FRAGILE,
    "B": TileType.BRIDGE,
    "s": TileType.SOFT_SWITCH,
    "h": TileType.HEAVY_SWITCH,
    "x": TileType.SPLIT_SWITCH,
}


# load_level function takes a JSON file path as input and returns a Board object 
# -> Board indicates that the function returns an instance of the Board class  
def load_level(file_path: str) -> Board:
    with open(file_path, 'r') as file:
        data = json.load(file)

    name = data.get("name", "Unnamed level") # get the level name from the JSON file.
    
    # Get the raw grid from the JSON file.
    # Example:
    # [
    #     "#####",
    #     "#S..#",
    #     "###G#"
    # ]
    raw_grid = data["grid"] 
    if not raw_grid:
        raise ValueError("Level grid must not be empty")
    
    raw_bridges = data.get("bridges", [])
    raw_switches = data.get("switches", [])

    cols = len(raw_grid[0])
    grid = [] # This will store the converted grid using TileType values
    start = None
    goal = None

    for row_idx, line in enumerate(raw_grid):
        # Check if all rows have the same length (same columns)
        if len(line) != cols:
            raise ValueError("All rows in the grid must have the same length")
        
        # This list stores the converted tiles for the current row
        row = [] 
        for col_idx, char in enumerate(line):
            if char not in CHAR_TO_TILE:
                raise ValueError(f"Unknown tile character '{char}' at row {row_idx}, col {col_idx} in level '{name}'")
            
            if char == "S":
                if start is not None:
                    raise ValueError(f"Level must have exactly one start tile S")
                start = (row_idx, col_idx)

            elif char == "G":
                if goal is not None:
                    raise ValueError(f"Level must have exactly one goal tile G")
                goal = (row_idx, col_idx)

            # Convert the character to its corresponding TileType
            # and add it to the current row
            row.append(CHAR_TO_TILE[char])

        # Add the converted row to the final grid.
        grid.append(row)

    # After scanning the whole grid, make sure a start tile exists.
    if start is None:
        raise ValueError("Level must have a start tile S")
    
    if goal is None:
        raise ValueError("Level must have a goal tile G")
    
    validate_metadata(
        grid=grid,
        bridges=raw_bridges,
        switches=raw_switches,
        level_name=name
    )
    
    return Board(name=name, 
                 grid=grid, 
                 start=start, 
                 goal=goal, 
                 bridges=raw_bridges,
                 switches=raw_switches)


def validate_metadata(grid, bridges, switches, level_name):
    rows = len(grid)
    cols = len(grid[0])

    def check_position(position, label):
        if (
            not isinstance(position, list)
            or len(position) != 2
        ):
            raise ValueError(f"Invalid {label} position format in level '{level_name}': {position}")

        row, col = position

        if not (0 <= row < rows and 0 <= col < cols):
            raise ValueError(f"{label} position {position} is out of bounds in level '{level_name}'")

        return row, col

    # Validate bridges
    for bridge in bridges:
        bridge_id = bridge["id"]

        if bridge_id < 0 or bridge_id >= len(bridges):
            raise ValueError(f"Invalid bridge id {bridge_id} in level '{level_name}'")

        for position in bridge["positions"]:
            row, col = check_position(position, "Bridge")

            if grid[row][col] != TileType.BRIDGE:
                raise ValueError(
                    f"Bridge metadata points to ({row}, {col}), "
                    f"but this cell is not a BRIDGE tile in level '{level_name}'"
                )

    # Validate switches
    for switch in switches:
        row, col = check_position(switch["position"], "Switch")

        switch_type = switch["type"]
        tile = grid[row][col]

        if switch_type == "soft" and tile != TileType.SOFT_SWITCH:
            raise ValueError(
                f"Soft switch metadata points to ({row}, {col}), "
                f"but this cell is not a SOFT_SWITCH tile in level '{level_name}'"
            )

        elif switch_type == "heavy" and tile != TileType.HEAVY_SWITCH:
            raise ValueError(
                f"Heavy switch metadata points to ({row}, {col}), "
                f"but this cell is not a HEAVY_SWITCH tile in level '{level_name}'"
            )

        elif switch_type == "split" and tile != TileType.SPLIT_SWITCH:
            raise ValueError(
                f"Split switch metadata points to ({row}, {col}), "
                f"but this cell is not a SPLIT_SWITCH tile in level '{level_name}'"
            )

        elif switch_type not in {"soft", "heavy", "split"}:
            raise ValueError(f"Unknown switch type '{switch_type}' in level '{level_name}'")

        # A switch may use either:
        # 1. bridge_ids + behavior
        # 2. effects containing multiple groups with different behaviors
        effects = switch.get("effects")

        if effects is None:
            effects = [
                {
                    "bridge_ids": switch.get("bridge_ids", []),
                    "behavior": switch.get("behavior", "toggle")
                }
            ]

        elif not isinstance(effects, list) or not effects:
            raise ValueError(
                f"Switch at ({row}, {col}) has invalid effects "
                f"in level '{level_name}'"
            )

        for effect in effects:
            behavior = effect.get("behavior", "toggle")

            if behavior not in {"toggle", "open", "close"}:
                raise ValueError(
                    f"Switch at ({row}, {col}) has unknown behavior "
                    f"'{behavior}' in level '{level_name}'"
                )

            bridge_ids = effect.get("bridge_ids", [])

            if not isinstance(bridge_ids, list):
                raise ValueError(
                    f"Switch at ({row}, {col}) must have bridge_ids as a list "
                    f"in level '{level_name}'"
                )

            for bridge_id in bridge_ids:
                if (
                    not isinstance(bridge_id, int)
                    or bridge_id < 0
                    or bridge_id >= len(bridges)
                ):
                    raise ValueError(
                        f"Switch at ({row}, {col}) refers to invalid bridge id "
                        f"{bridge_id} in level '{level_name}'"
                    )

        # Split switch must define cube teleport positions.
        if switch_type == "split":
            if "cube1" not in switch or "cube2" not in switch:
                raise ValueError(
                    f"Split switch at ({row}, {col}) must define cube1 and cube2 "
                    f"in level '{level_name}'"
                )

            cube1_row, cube1_col = check_position(switch["cube1"], "Split cube1")
            cube2_row, cube2_col = check_position(switch["cube2"], "Split cube2")

            if (cube1_row, cube1_col) == (cube2_row, cube2_col):
                raise ValueError(
                    f"Split switch at ({row}, {col}) creates two cubes at the same position "
                    f"in level '{level_name}'"
                )

            if grid[cube1_row][cube1_col] == TileType.VOID:
                raise ValueError(
                    f"Split cube1 position ({cube1_row}, {cube1_col}) is VOID "
                    f"in level '{level_name}'"
                )

            if grid[cube2_row][cube2_col] == TileType.VOID:
                raise ValueError(
                    f"Split cube2 position ({cube2_row}, {cube2_col}) is VOID "
                    f"in level '{level_name}'"
                )