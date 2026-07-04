import pytest

from core.board import Board
from core.game import Game, SWITCH_CUBE
from core.state import State, Orientation, BlockMode
from core.tiles import TileType


def make_advanced_board() -> Board:
    """
    Create a compact board for testing advanced mechanics.

    Important positions:
    - (1, 2): fragile tile
    - (1, 3): soft switch
    - (1, 4): heavy switch
    - (3, 5): bridge tile
    - (3, 3): split switch
    - (5, 6): goal
    """
    rows = 6
    cols = 7

    grid = [
        [TileType.FLOOR for _ in range(cols)]
        for _ in range(rows)
    ]

    grid[1][2] = TileType.FRAGILE
    grid[1][3] = TileType.SOFT_SWITCH
    grid[1][4] = TileType.HEAVY_SWITCH
    grid[3][5] = TileType.BRIDGE
    grid[3][3] = TileType.SPLIT_SWITCH
    grid[5][6] = TileType.GOAL

    bridges = [
        {
            "id": 0,
            "positions": [[3, 5]],
            "initial_open": False
        }
    ]

    switches = [
        {
            "position": [1, 3],
            "type": "soft",
            "bridge_ids": [0],
            "behavior": "toggle"
        },
        {
            "position": [1, 4],
            "type": "heavy",
            "bridge_ids": [0],
            "behavior": "open"
        },
        {
            "position": [3, 3],
            "type": "split",
            "cube1": [2, 1],
            "cube2": [4, 1]
        }
    ]

    return Board(
        name="Advanced Mechanics Test Board",
        grid=grid,
        start=(1, 1),
        goal=(5, 6),
        bridges=bridges,
        switches=switches
    )


def make_split_state(
    bridges=(False,),
    cube1=(2, 1),
    cube2=(2, 4),
    active_cube=1
) -> State:
    return State(
        row=0,
        col=0,
        orientation=Orientation.STANDING,
        bridges=bridges,
        mode=BlockMode.SPLIT,
        cube1=cube1,
        cube2=cube2,
        active_cube=active_cube
    )


def test_fragile_tile_rejects_standing_block():
    board = make_advanced_board()
    game = Game(board)

    state = State(
        row=1,
        col=2,
        orientation=Orientation.STANDING,
        bridges=board.initial_bridges
    )

    assert game.is_valid_state(state) is False


def test_fragile_tile_accepts_lying_block():
    board = make_advanced_board()
    game = Game(board)

    # Occupies (1, 1) floor and (1, 2) fragile.
    # Lying across fragile tile is allowed.
    state = State(
        row=1,
        col=1,
        orientation=Orientation.HORIZONTAL,
        bridges=board.initial_bridges
    )

    assert game.is_valid_state(state) is True


def test_closed_bridge_is_invalid():
    board = make_advanced_board()
    game = Game(board)

    state = State(
        row=3,
        col=5,
        orientation=Orientation.STANDING,
        bridges=(False,)
    )

    assert game.is_valid_state(state) is False


def test_open_bridge_is_valid():
    board = make_advanced_board()
    game = Game(board)

    state = State(
        row=3,
        col=5,
        orientation=Orientation.STANDING,
        bridges=(True,)
    )

    assert game.is_valid_state(state) is True


def test_bridge_tile_without_metadata_raises_error():
    grid = [
        [TileType.FLOOR, TileType.FLOOR, TileType.FLOOR],
        [TileType.FLOOR, TileType.BRIDGE, TileType.FLOOR],
        [TileType.FLOOR, TileType.FLOOR, TileType.GOAL],
    ]

    board = Board(
        name="Broken Bridge Metadata Board",
        grid=grid,
        start=(0, 0),
        goal=(2, 2),
        bridges=[]
    )

    game = Game(board)

    state = State(
        row=1,
        col=1,
        orientation=Orientation.STANDING,
        bridges=()
    )

    with pytest.raises(ValueError):
        game.is_valid_state(state)


def test_soft_switch_toggles_bridge_when_standing():
    board = make_advanced_board()
    game = Game(board)

    state = State(
        row=1,
        col=3,
        orientation=Orientation.STANDING,
        bridges=(False,)
    )

    next_state = game.apply_switches(state)

    assert next_state.bridges == (True,)


def test_soft_switch_toggles_bridge_when_lying_across_it():
    board = make_advanced_board()
    game = Game(board)

    # Occupies (1, 2) fragile and (1, 3) soft switch.
    # Soft switch activates even when block is lying.
    state = State(
        row=1,
        col=2,
        orientation=Orientation.HORIZONTAL,
        bridges=(False,)
    )

    next_state = game.apply_switches(state)

    assert next_state.bridges == (True,)


def test_heavy_switch_opens_bridge_when_standing():
    board = make_advanced_board()
    game = Game(board)

    state = State(
        row=1,
        col=4,
        orientation=Orientation.STANDING,
        bridges=(False,)
    )

    next_state = game.apply_switches(state)

    assert next_state.bridges == (True,)


def test_heavy_switch_does_not_activate_when_lying():
    board = make_advanced_board()
    game = Game(board)

    # Occupies (1, 4) heavy switch and (1, 5) normal floor.
    # Heavy switch does not activate because the block is lying.
    state = State(
        row=1,
        col=4,
        orientation=Orientation.HORIZONTAL,
        bridges=(False,)
    )

    next_state = game.apply_switches(state)

    assert next_state.bridges == (False,)


@pytest.mark.parametrize(
    "behavior, initial_bridge_state, expected_bridge_state",
    [
        ("toggle", False, True),
        ("open", False, True),
        ("close", True, False),
    ]
)
def test_activate_switch_behaviors(
    behavior,
    initial_bridge_state,
    expected_bridge_state
):
    board = make_advanced_board()
    game = Game(board)

    switch = {
        "bridge_ids": [0],
        "behavior": behavior
    }

    bridge_states = [initial_bridge_state]

    game.activate_switch(switch, bridge_states)

    assert bridge_states == [expected_bridge_state]


def test_split_switch_creates_split_state_when_standing():
    board = make_advanced_board()
    game = Game(board)

    state = State(
        row=3,
        col=3,
        orientation=Orientation.STANDING,
        bridges=board.initial_bridges
    )

    next_state = game.apply_switches(state)

    assert next_state.mode == BlockMode.SPLIT
    assert next_state.cube1 == (2, 1)
    assert next_state.cube2 == (4, 1)
    assert next_state.active_cube == 1


def test_lying_on_split_switch_does_not_split():
    board = make_advanced_board()
    game = Game(board)

    # Occupies (3, 2) floor and (3, 3) split switch.
    # Split switch requires standing block.
    state = State(
        row=3,
        col=2,
        orientation=Orientation.HORIZONTAL,
        bridges=board.initial_bridges
    )

    next_state = game.apply_switches(state)

    assert next_state.mode == BlockMode.NORMAL
    assert next_state.orientation == Orientation.HORIZONTAL


def test_switch_active_cube_changes_control():
    board = make_advanced_board()
    game = Game(board)

    state = make_split_state(active_cube=1)

    next_state = game.apply_move(state, SWITCH_CUBE)

    assert next_state.mode == BlockMode.SPLIT
    assert next_state.active_cube == 2
    assert next_state.cube1 == state.cube1
    assert next_state.cube2 == state.cube2


def test_move_active_cube_moves_only_active_cube():
    board = make_advanced_board()
    game = Game(board)

    state = make_split_state(
        cube1=(2, 1),
        cube2=(2, 4),
        active_cube=1
    )

    next_state = game.apply_move(state, "RIGHT")

    assert next_state.mode == BlockMode.SPLIT
    assert next_state.cube1 == (2, 2)
    assert next_state.cube2 == (2, 4)
    assert next_state.active_cube == 1


def test_split_cube_can_activate_soft_switch():
    board = make_advanced_board()
    game = Game(board)

    # cube1 moves from (1, 2) to (1, 3), which is a soft switch.
    state = make_split_state(
        bridges=(False,),
        cube1=(1, 2),
        cube2=(2, 6),
        active_cube=1
    )

    next_state = game.apply_move(state, "RIGHT")

    assert next_state.mode == BlockMode.SPLIT
    assert next_state.cube1 == (1, 3)
    assert next_state.bridges == (True,)


def test_split_cube_cannot_activate_heavy_switch():
    board = make_advanced_board()
    game = Game(board)

    # cube1 moves from (1, 3) to (1, 4), which is a heavy switch.
    # A single split cube must not activate a heavy switch.
    state = make_split_state(
        bridges=(False,),
        cube1=(1, 3),
        cube2=(2, 6),
        active_cube=1
    )

    next_state = game.apply_move(state, "RIGHT")

    assert next_state.mode == BlockMode.SPLIT
    assert next_state.cube1 == (1, 4)
    assert next_state.bridges == (False,)


def test_cube_cannot_move_onto_other_cube_cell():
    board = make_advanced_board()
    game = Game(board)

    state = make_split_state(
        cube1=(2, 1),
        cube2=(2, 2),
        active_cube=1
    )

    next_state = game.apply_move(state, "RIGHT")

    assert next_state is None


def test_cubes_merge_horizontally_when_adjacent():
    board = make_advanced_board()
    game = Game(board)

    # cube1 moves from (2, 1) to (2, 2),
    # then it becomes adjacent to cube2 at (2, 3).
    state = make_split_state(
        cube1=(2, 1),
        cube2=(2, 3),
        active_cube=1
    )

    next_state = game.apply_move(state, "RIGHT")

    assert next_state.mode == BlockMode.NORMAL
    assert next_state.orientation == Orientation.HORIZONTAL
    assert next_state.row == 2
    assert next_state.col == 2


def test_cubes_merge_vertically_when_adjacent():
    board = make_advanced_board()
    game = Game(board)

    # cube1 moves from (1, 2) to (2, 2),
    # then it becomes adjacent to cube2 at (3, 2).
    state = make_split_state(
        cube1=(1, 2),
        cube2=(3, 2),
        active_cube=1
    )

    next_state = game.apply_move(state, "DOWN")

    assert next_state.mode == BlockMode.NORMAL
    assert next_state.orientation == Orientation.VERTICAL
    assert next_state.row == 2
    assert next_state.col == 2


def test_split_cube_cannot_win_even_if_cube_is_on_goal():
    board = make_advanced_board()
    game = Game(board)

    state = make_split_state(
        cube1=board.goal,
        cube2=(5, 5),
        active_cube=1
    )

    assert game.is_goal_state(state) is False


def test_get_successors_in_split_mode_includes_switch_action():
    board = make_advanced_board()
    game = Game(board)

    state = make_split_state(
        cube1=(2, 1),
        cube2=(2, 4),
        active_cube=1
    )

    successors = game.get_successors(state)
    actions = [action for action, next_state, cost in successors]

    assert SWITCH_CUBE in actions

    for action, next_state, cost in successors:
        assert next_state is not None
        assert cost == 1