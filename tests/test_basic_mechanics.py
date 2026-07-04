import json

import pytest

from core.board import Board
from core.game import Game
from core.level_loader import load_level
from core.state import State, Orientation, BlockMode
from core.tiles import TileType
from core.block import get_occupied_tiles, move_block


def make_basic_board() -> Board:
    """
    Create a small board for testing only basic mechanics.

    V = void
    F = floor
    G = goal

    Grid:
        V V V V V
        V F F F V
        V F G F V
        V F F F V
        V V V V V

    Start = (1, 1)
    Goal  = (2, 2)
    """
    grid = [
        [TileType.VOID, TileType.VOID,  TileType.VOID, TileType.VOID,  TileType.VOID],
        [TileType.VOID, TileType.FLOOR, TileType.FLOOR, TileType.FLOOR, TileType.VOID],
        [TileType.VOID, TileType.FLOOR, TileType.GOAL,  TileType.FLOOR, TileType.VOID],
        [TileType.VOID, TileType.FLOOR, TileType.FLOOR, TileType.FLOOR, TileType.VOID],
        [TileType.VOID, TileType.VOID,  TileType.VOID, TileType.VOID,  TileType.VOID],
    ]

    return Board(
        name="Basic Mechanics Test Board",
        grid=grid,
        start=(1, 1),
        goal=(2, 2)
    )


def test_load_basic_level_from_json(tmp_path):
    """
    Test that level_loader can load a simple basic level.
    """
    level_data = {
        "name": "Loader Basic Test",
        "grid": [
            "S#G"
        ]
    }

    level_file = tmp_path / "basic_loader_test.json"
    level_file.write_text(json.dumps(level_data), encoding="utf-8")

    board = load_level(str(level_file))

    assert board.name == "Loader Basic Test"
    assert board.rows == 1
    assert board.cols == 3
    assert board.start == (0, 0)
    assert board.goal == (0, 2)

    assert board.get_tile(0, 0) == TileType.FLOOR
    assert board.get_tile(0, 1) == TileType.FLOOR
    assert board.get_tile(0, 2) == TileType.GOAL


def test_initial_state_is_standing_on_start():
    board = make_basic_board()
    game = Game(board)

    assert game.state == State(
        row=1,
        col=1,
        orientation=Orientation.STANDING,
        bridges=()
    )

    assert game.state.mode == BlockMode.NORMAL


@pytest.mark.parametrize(
    "state, expected_tiles",
    [
        (
            State(row=1, col=1, orientation=Orientation.STANDING),
            [(1, 1)]
        ),
        (
            State(row=1, col=1, orientation=Orientation.HORIZONTAL),
            [(1, 1), (1, 2)]
        ),
        (
            State(row=1, col=1, orientation=Orientation.VERTICAL),
            [(1, 1), (2, 1)]
        ),
    ]
)
def test_get_occupied_tiles_for_normal_block(state, expected_tiles):
    assert get_occupied_tiles(state) == expected_tiles


@pytest.mark.parametrize(
    "state, direction, expected_state",
    [
        # STANDING
        (
            State(row=5, col=5, orientation=Orientation.STANDING),
            "UP",
            State(row=3, col=5, orientation=Orientation.VERTICAL)
        ),
        (
            State(row=5, col=5, orientation=Orientation.STANDING),
            "DOWN",
            State(row=6, col=5, orientation=Orientation.VERTICAL)
        ),
        (
            State(row=5, col=5, orientation=Orientation.STANDING),
            "LEFT",
            State(row=5, col=3, orientation=Orientation.HORIZONTAL)
        ),
        (
            State(row=5, col=5, orientation=Orientation.STANDING),
            "RIGHT",
            State(row=5, col=6, orientation=Orientation.HORIZONTAL)
        ),

        # HORIZONTAL
        (
            State(row=5, col=5, orientation=Orientation.HORIZONTAL),
            "UP",
            State(row=4, col=5, orientation=Orientation.HORIZONTAL)
        ),
        (
            State(row=5, col=5, orientation=Orientation.HORIZONTAL),
            "DOWN",
            State(row=6, col=5, orientation=Orientation.HORIZONTAL)
        ),
        (
            State(row=5, col=5, orientation=Orientation.HORIZONTAL),
            "LEFT",
            State(row=5, col=4, orientation=Orientation.STANDING)
        ),
        (
            State(row=5, col=5, orientation=Orientation.HORIZONTAL),
            "RIGHT",
            State(row=5, col=7, orientation=Orientation.STANDING)
        ),

        # VERTICAL
        (
            State(row=5, col=5, orientation=Orientation.VERTICAL),
            "UP",
            State(row=4, col=5, orientation=Orientation.STANDING)
        ),
        (
            State(row=5, col=5, orientation=Orientation.VERTICAL),
            "DOWN",
            State(row=7, col=5, orientation=Orientation.STANDING)
        ),
        (
            State(row=5, col=5, orientation=Orientation.VERTICAL),
            "LEFT",
            State(row=5, col=4, orientation=Orientation.VERTICAL)
        ),
        (
            State(row=5, col=5, orientation=Orientation.VERTICAL),
            "RIGHT",
            State(row=5, col=6, orientation=Orientation.VERTICAL)
        ),
    ]
)
def test_move_block_transition_table(state, direction, expected_state):
    assert move_block(state, direction) == expected_state


def test_invalid_direction_raises_error():
    state = State(row=1, col=1, orientation=Orientation.STANDING)

    with pytest.raises(ValueError):
        move_block(state, "JUMP")


def test_is_valid_state_accepts_fully_supported_block():
    board = make_basic_board()
    game = Game(board)

    state = State(row=1, col=2, orientation=Orientation.HORIZONTAL)

    assert game.is_valid_state(state) is True


def test_is_valid_state_rejects_void_cell():
    board = make_basic_board()
    game = Game(board)

    # (0, 0) is VOID.
    state = State(row=0, col=0, orientation=Orientation.STANDING)

    assert game.is_valid_state(state) is False


def test_is_valid_state_rejects_out_of_bounds():
    board = make_basic_board()
    game = Game(board)

    # Horizontal block occupies (1, 4) and (1, 5).
    # (1, 5) is outside the board.
    state = State(row=1, col=4, orientation=Orientation.HORIZONTAL)

    assert game.is_valid_state(state) is False


def test_move_updates_state_when_valid():
    board = make_basic_board()
    game = Game(board)

    moved = game.move("RIGHT")

    assert moved is True
    assert game.state == State(
        row=1,
        col=2,
        orientation=Orientation.HORIZONTAL,
        bridges=()
    )


def test_move_does_not_update_state_when_invalid():
    board = make_basic_board()
    game = Game(board)

    original_state = game.state

    moved = game.move("LEFT")

    assert moved is False
    assert game.state == original_state


def test_goal_requires_standing_on_goal():
    board = make_basic_board()
    game = Game(board)

    standing_on_goal = State(row=2, col=2, orientation=Orientation.STANDING)
    lying_across_goal = State(row=2, col=1, orientation=Orientation.HORIZONTAL)

    assert game.is_goal_state(standing_on_goal) is True
    assert game.is_goal_state(lying_across_goal) is False


def test_split_state_cannot_be_goal_even_if_cube_on_goal():
    board = make_basic_board()
    game = Game(board)

    split_state = State(
        row=0,
        col=0,
        orientation=Orientation.STANDING,
        bridges=(),
        mode=BlockMode.SPLIT,
        cube1=(2, 2),
        cube2=(3, 2),
        active_cube=1
    )

    assert game.is_goal_state(split_state) is False


def test_get_successors_returns_only_valid_moves():
    board = make_basic_board()
    game = Game(board)

    successors = game.get_successors(game.initial_state)

    actions = [action for action, next_state, cost in successors]

    # From start (1, 1):
    # UP and LEFT are invalid because the block falls outside/onto void.
    # DOWN and RIGHT are valid.
    assert "DOWN" in actions
    assert "RIGHT" in actions
    assert "UP" not in actions
    assert "LEFT" not in actions

    for action, next_state, cost in successors:
        assert game.is_valid_state(next_state) is True
        assert cost == 1


def test_reset_restores_initial_state():
    board = make_basic_board()
    game = Game(board)

    assert game.move("RIGHT") is True
    assert game.state != game.initial_state

    game.reset()

    assert game.state == game.initial_state