import json

import pytest

from core.level_loader import load_level
from core.tiles import TileType


def write_level(tmp_path, data):
    """
    Helper function:
    Create a temporary JSON level file and return its path.
    """
    level_file = tmp_path / "test_level.json"
    level_file.write_text(json.dumps(data), encoding="utf-8")
    return str(level_file)


def test_load_valid_basic_level(tmp_path):
    data = {
        "name": "Valid Basic Level",
        "grid": [
            "S#G"
        ]
    }

    path = write_level(tmp_path, data)
    board = load_level(path)

    assert board.name == "Valid Basic Level"
    assert board.rows == 1
    assert board.cols == 3
    assert board.start == (0, 0)
    assert board.goal == (0, 2)

    assert board.get_tile(0, 0) == TileType.FLOOR
    assert board.get_tile(0, 1) == TileType.FLOOR
    assert board.get_tile(0, 2) == TileType.GOAL

    assert board.bridges == []
    assert board.switches == []
    assert board.initial_bridges == ()


def test_load_valid_advanced_level_metadata(tmp_path):
    data = {
        "name": "Valid Advanced Level",
        "grid": [
            "S#BshxG",
            "#######",
            "#######"
        ],
        "bridges": [
            {
                "id": 0,
                "positions": [[0, 2]],
                "initial_open": True
            }
        ],
        "switches": [
            {
                "position": [0, 3],
                "type": "soft",
                "bridge_ids": [0],
                "behavior": "toggle"
            },
            {
                "position": [0, 4],
                "type": "heavy",
                "bridge_ids": [0],
                "behavior": "open"
            },
            {
                "position": [0, 5],
                "type": "split",
                "cube1": [1, 1],
                "cube2": [2, 1]
            }
        ]
    }

    path = write_level(tmp_path, data)
    board = load_level(path)

    assert board.name == "Valid Advanced Level"
    assert board.start == (0, 0)
    assert board.goal == (0, 6)

    assert board.get_tile(0, 2) == TileType.BRIDGE
    assert board.get_tile(0, 3) == TileType.SOFT_SWITCH
    assert board.get_tile(0, 4) == TileType.HEAVY_SWITCH
    assert board.get_tile(0, 5) == TileType.SPLIT_SWITCH

    assert board.initial_bridges == (True,)
    assert board.get_bridge_id(0, 2) == 0

    assert board.get_switch(0, 3)["type"] == "soft"
    assert board.get_switch(0, 4)["type"] == "heavy"
    assert board.get_switch(0, 5)["type"] == "split"


def test_empty_grid_raises_error(tmp_path):
    data = {
        "name": "Empty Grid",
        "grid": []
    }

    path = write_level(tmp_path, data)

    with pytest.raises(ValueError):
        load_level(path)


def test_unequal_row_lengths_raise_error(tmp_path):
    data = {
        "name": "Unequal Row Lengths",
        "grid": [
            "S#",
            "###G"
        ]
    }

    path = write_level(tmp_path, data)

    with pytest.raises(ValueError):
        load_level(path)


def test_unknown_tile_character_raises_error(tmp_path):
    data = {
        "name": "Unknown Character",
        "grid": [
            "S?G"
        ]
    }

    path = write_level(tmp_path, data)

    with pytest.raises(ValueError):
        load_level(path)


@pytest.mark.parametrize(
    "grid",
    [
        ["###G"],   # missing start
        ["S###"],   # missing goal
        ["S#SG"],   # multiple starts
        ["S#GG"],   # multiple goals
    ]
)
def test_start_and_goal_validation_errors(tmp_path, grid):
    data = {
        "name": "Invalid Start Goal",
        "grid": grid
    }

    path = write_level(tmp_path, data)

    with pytest.raises(ValueError):
        load_level(path)


def test_bridge_metadata_must_point_to_bridge_tile(tmp_path):
    data = {
        "name": "Bridge Metadata Wrong Tile",
        "grid": [
            "S#G"
        ],
        "bridges": [
            {
                "id": 0,
                "positions": [[0, 1]],
                "initial_open": False
            }
        ]
    }

    path = write_level(tmp_path, data)

    # Position (0, 1) is FLOOR '#', not BRIDGE 'B'.
    with pytest.raises(ValueError):
        load_level(path)


@pytest.mark.parametrize(
    "switch_type, tile_char",
    [
        ("soft", "h"),   # soft metadata points to heavy tile
        ("heavy", "s"),  # heavy metadata points to soft tile
        ("split", "s"),  # split metadata points to soft tile
    ]
)
def test_switch_metadata_must_match_switch_tile_type(tmp_path, switch_type, tile_char):
    data = {
        "name": "Switch Metadata Wrong Tile",
        "grid": [
            f"S#{tile_char}G"
        ],
        "switches": [
            {
                "position": [0, 2],
                "type": switch_type
            }
        ]
    }

    path = write_level(tmp_path, data)

    with pytest.raises(ValueError):
        load_level(path)


def test_switch_cannot_reference_invalid_bridge_id(tmp_path):
    data = {
        "name": "Invalid Bridge Id In Switch",
        "grid": [
            "S#sG"
        ],
        "switches": [
            {
                "position": [0, 2],
                "type": "soft",
                "bridge_ids": [0],
                "behavior": "toggle"
            }
        ]
    }

    path = write_level(tmp_path, data)

    # There is no bridge with id 0.
    with pytest.raises(ValueError):
        load_level(path)


@pytest.mark.parametrize(
    "switch_data",
    [
        # Missing cube1 and cube2
        {
            "position": [0, 2],
            "type": "split"
        },

        # cube1 and cube2 are the same position
        {
            "position": [0, 2],
            "type": "split",
            "cube1": [1, 1],
            "cube2": [1, 1]
        },

        # cube1 is on VOID
        {
            "position": [0, 2],
            "type": "split",
            "cube1": [1, 1],
            "cube2": [1, 2]
        },
    ]
)
def test_split_switch_metadata_validation_errors(tmp_path, switch_data):
    data = {
        "name": "Invalid Split Metadata",
        "grid": [
            "S#xG",
            "...."
        ],
        "switches": [
            switch_data
        ]
    }

    path = write_level(tmp_path, data)

    with pytest.raises(ValueError):
        load_level(path)