from core.state import State, Orientation, BlockMode
from core.tiles import TileType
from core.block import (
    DIRECTIONS, 
    move_block, 
    get_occupied_tiles,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)


SWITCH_CUBE = "SWITCH"

CUBE_MOVE_DELTAS = {
    UP: (-1, 0),
    DOWN: (1, 0),
    LEFT:  (0, -1),
    RIGHT: (0, 1)
}


class Game:
    def __init__(self, board):
        self.board = board
        self.initial_state = self.create_initial_state()
        self.state = self.initial_state


    def create_initial_state(self):
        start_row, start_col = self.board.start

        return State(
            row = start_row,
            col = start_col,
            orientation = Orientation.STANDING,
            bridges=self.board.initial_bridges,
        )
    
    
    def is_valid_state(self, state: State) -> bool:
        occupied_tiles = get_occupied_tiles(state)

        for row, col in occupied_tiles:
            tile = self.board.get_tile(row, col)

            if (
                tile is None 
                or tile == TileType.VOID
                or (
                    tile == TileType.FRAGILE 
                    and state.orientation == Orientation.STANDING
                    and state.mode == BlockMode.NORMAL
                ) # case for Fragile
            ):
                return False
            
            # Bridge rules
            if tile == TileType.BRIDGE:
                bridge_id = self.board.get_bridge_id(row, col)

                if bridge_id is None:
                    raise ValueError(
                        f"Bridge tile at ({row}, {col}) has no bridge id. "
                        "Check the level JSON bridges metadata."
                    )
        
                if bridge_id >= len(state.bridges):
                    raise ValueError(
                        f"Bridge id {bridge_id} at ({row}, {col}) is out of range "
                        f"for state.bridges={state.bridges}."
                    )
                
                if state.bridges[bridge_id] is False:
                    return False

        return True
    
    
    def create_split_state(self, state: State, switch: dict, bridges: tuple) -> State:
        if "cube1" not in switch or "cube2" not in switch:
            raise ValueError("Split switch must define cube1 and cube2 positions.")
        
        cube1 = tuple(switch["cube1"])
        cube2 = tuple(switch["cube2"])

        if cube1 == cube2:
            raise ValueError("Split switch cannot create two cubes at the same position.")

        split_state = State(
            row=state.row,
            col=state.col,
            orientation=state.orientation,
            bridges=bridges,
            mode=BlockMode.SPLIT,
            cube1=cube1,
            cube2=cube2,
            active_cube=1
        )

        if not self.is_valid_state(split_state):
            raise ValueError(
                f"Split switch creates invalid cube positions: cube1={cube1}, cube2={cube2}"
            )
        
        return split_state


    # Switches
    def apply_switches(
            self, 
            state: State,
            trigger_positions: list[tuple[int, int]] | None = None
        ) -> State:
        """
        Apply switches pressed by the block/cube.

        trigger_positions:
            - None: check all occupied tiles. Used for normal block movement.
            - list of positions: check only the cube positions that just moved.
            Used in split mode to avoid re-triggering switches under inactive cubes.
        """
        new_bridges = list(state.bridges)
        
        if trigger_positions is None:
            trigger_positions = get_occupied_tiles(state)

        for row, col in trigger_positions:
            tile = self.board.get_tile(row, col)

            if tile == TileType.SOFT_SWITCH:
                switch = self.board.get_switch(row, col)

                if switch is None:
                    raise ValueError(
                        f"Soft switch tile at ({row}, {col}) has no switch metadata."
                    )
                
                # Soft switch can be activated by the normal block or by a split cube.
                self.activate_switch(switch, new_bridges)
            
            elif tile == TileType.HEAVY_SWITCH:
                # Heavy switch works only when the normal block is standing exactly on it.
                # A split cube must not activate a heavy switch.
                if state.orientation == Orientation.STANDING and state.mode == BlockMode.NORMAL:
                    switch = self.board.get_switch(row, col)

                    if switch is None:
                        raise ValueError(
                            f"Heavy switch tile at ({row}, {col}) has no switch metadata."
                        )
                    self.activate_switch(switch, new_bridges)

            elif tile == TileType.SPLIT_SWITCH:
                # Split switch works only when the normal block is standing on it.
                if state.mode == BlockMode.NORMAL and state.orientation == Orientation.STANDING:
                    switch = self.board.get_switch(row, col)

                    if switch is None:
                        raise ValueError(
                            f"Split switch tile at ({row}, {col}) has no switch metadata."
                        )
                    
                    # Optional: a split switch may also control bridges.
                    if switch.get("bridge_ids"):
                        self.activate_switch(switch, new_bridges)

                    # Then split the block into two cubes.
                    return self.create_split_state(
                        state=state,
                        switch=switch,
                        bridges=tuple(new_bridges)
                    )
        
        return State(
            row=state.row,
            col=state.col,
            orientation=state.orientation,
            bridges=tuple(new_bridges),
            mode=state.mode,
            cube1=state.cube1,
            cube2=state.cube2,
            active_cube=state.active_cube
        )
    

    def activate_switch(self, switch: dict, bridge_states: list[bool]):
        """
        Update bridge states according to the switch behavior.

        Supported behaviors:
        - "toggle": open becomes closed, closed becomes open
        - "open": permanently set linked bridges to open
        - "close": permanently set linked bridges to closed
        """
        behavior = switch.get("behavior", "toggle")
        bridge_ids = switch.get("bridge_ids", [])

        for bridge_id in bridge_ids:
            if bridge_id < 0 or bridge_id >= len(bridge_states):
                raise ValueError(f"Invalid bridge id in switch: {bridge_id}")

            if behavior == "toggle":
                bridge_states[bridge_id] = not bridge_states[bridge_id]

            elif behavior == "open":
                bridge_states[bridge_id] = True

            elif behavior == "close":
                bridge_states[bridge_id] = False

            else:
                raise ValueError(f"Unknown switch behavior: {behavior}")


    def move_active_cube(self, state: State, direction: str) -> State | None:
        """
        Move the currently active cube by one cell in split mode.

        Only the active cube moves. The other cube stays in place.
        """
        if state.mode != BlockMode.SPLIT:
            return None
        
        if state.cube1 is None or state.cube2 is None:
            raise ValueError("Split state must have cube1 and cube2 positions.")
        
        direction = direction.upper()

        if direction not in CUBE_MOVE_DELTAS:
            raise ValueError(f"Invalid cube move direction: {direction}")
        
        dr, dc = CUBE_MOVE_DELTAS[direction] # delta row, delta col

        cube1 = state.cube1
        cube2 = state.cube2

        if state.active_cube == 1:
            old_row, old_col = cube1
            new_cube1 = (old_row + dr, old_col + dc)
            new_cube2 = cube2

            # A cube cannot move onto the other cube's cell.
            if new_cube1 == new_cube2:
                return None
            
            moved_position = new_cube1
        
        elif state.active_cube == 2:
            old_row, old_col = cube2
            new_cube1 = cube1
            new_cube2 = (old_row + dr, old_col + dc)

            if new_cube2 == new_cube1:
                return None
            
            moved_position = new_cube2

        else:
            raise ValueError(f"Invalid active cube: {state.active_cube}")

        next_state = State(
            row=state.row,
            col=state.col,
            orientation=state.orientation,
            bridges=state.bridges,
            mode=BlockMode.SPLIT,
            cube1=new_cube1,
            cube2=new_cube2,
            active_cube=state.active_cube
        )

        # Check whether both cubes are still on valid tiles.
        if not self.is_valid_state(next_state):
            return None
        
        # Apply soft switch only for the cube that just moved.
        next_state = self.apply_switches(
            next_state,
            trigger_positions=[moved_position]
        )

        # Check again because a switch may close a bridge under a cube.
        if not self.is_valid_state(next_state):
            return None
        
        # If the two cubes become adjacent, merge them back into a normal block.
        next_state = self.merge_cubes_if_possible(next_state)

        if not self.is_valid_state(next_state):
            return None
        
        return next_state
    

    def merge_cubes_if_possible(self, state: State) -> State:
        """
        Merge two split cubes back into a normal 1x1x2 block
        if they are adjacent horizontally or vertically.
        """
        if state.mode != BlockMode.SPLIT:
            return state
        
        if state.cube1 is None or state.cube2 is None:
            raise ValueError("Split state must have cube1 and cube2 positions.")

        r1, c1 = state.cube1
        r2, c2 = state.cube2

        row_diff = abs(r1 - r2)
        col_diff = abs(c1 - c2)

        # They are not adjacent, so they cannot merge
        if row_diff + col_diff != 1:
            return state
        
        # Horizontal merge:
        # cubes are on the same row and neighboring columns
        if r1 == r2:
            return State(
                row=r1,
                col=min(c1, c2),
                orientation=Orientation.HORIZONTAL,
                bridges=state.bridges,
                mode=BlockMode.NORMAL
            )
        
        # Vertical merge:
        # cubes are on the same column and neighboring rows
        if c1 == c2:
            return State(
                row=min(r1, r2),
                col=c1,
                orientation=Orientation.VERTICAL,
                bridges=state.bridges,
                mode=BlockMode.NORMAL
            )
        
        raise RuntimeError("Invalid adjacent cube configuration")

        
    def apply_move(self, state: State, direction: str) -> State | None:
        direction = direction.upper()

        # Special action in split mode: switch the active cube.
        if direction in {SWITCH_CUBE, "SPACE"}:
            return self.switch_active_cube(state)
        
        # Split mode:
        # move only the active 1x1x1 cube.
        if state.mode == BlockMode.SPLIT:
            return self.move_active_cube(state, direction)

        # Normal 1x1x2 block movement.
        next_state = move_block(state, direction)

        # First check validity before activating switches.
        if not self.is_valid_state(next_state):
            return None
        
        # Then apply switches if the block presses any switch
        next_state = self.apply_switches(next_state)

        # Check again after switches.
        # This matters if a switch closes a bridge under the block.
        if not self.is_valid_state(next_state):
            return None
        
        return next_state
    

    def switch_active_cube(self, state: State) -> State | None:
        """
        Switch control between cube1 and cube2 in split mode.

        This corresponds to pressing Space in the original game.
        """
        if state.mode != BlockMode.SPLIT:
            return None
        
        if state.cube1 is None or state.cube2 is None:
            raise ValueError("Split state must have cube1 and cube2 positions.")
        
        if state.active_cube not in [1, 2]:
            raise ValueError(f"Invalid active cube: {state.active_cube}")
        
        new_active_cube = 2 if state.active_cube == 1 else 1

        return State(
            row=state.row,
            col=state.col,
            orientation=state.orientation,
            bridges=state.bridges,
            mode=BlockMode.SPLIT,
            cube1=state.cube1,
            cube2=state.cube2,
            active_cube=new_active_cube
        )


    def is_goal_state(self, state: State | None = None) -> bool:
        if state is None:
            state = self.state

        return (
            state.orientation == Orientation.STANDING
            and (state.row, state.col) == self.board.goal
            and state.mode == BlockMode.NORMAL
        )
    

    def get_successors(self, state: State) -> list[tuple[str, State, int]]:
        successors = []

        actions = list(DIRECTIONS)

        if state.mode == BlockMode.SPLIT:
            actions.append(SWITCH_CUBE)

        for action in actions:
            next_state = self.apply_move(state, action)
            
            if next_state is not None:
                cost = 1
                successors.append((action, next_state, cost))

        return successors
    

    def move(self, direction: str) -> bool:
        next_state = self.apply_move(self.state, direction)

        if next_state is None:
            return False
        
        self.state = next_state
        return True
    

    def reset(self):
        self.state = self.initial_state

    
    def is_win(self) -> bool:
        return self.is_goal_state(self.state)
    
    
    def get_occupied_tiles(self):
        return get_occupied_tiles(self.state)