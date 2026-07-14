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
from core.move_result import MoveResult, MoveStatus


SWITCH_CUBE = "SWITCH"

CUBE_MOVE_DELTAS = {
    UP: (-1, 0),
    DOWN: (1, 0),
    LEFT:  (0, -1),
    RIGHT: (0, 1)
}


NORMAL_MOVE_COST = 1
STANDIND_TO_LYING_COST = 2
HEAVY_SWITCH_COST = 3
FRAGILE_TILE_COST = 4


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
    

    def get_invalid_state_reason(
        self,
        state: State
    ) -> str | None:
        """
        Trả về lý do state không hợp lệ.

        None nghĩa là state hợp lệ.
        """
        occupied_tiles = get_occupied_tiles(state)

        for row, col in occupied_tiles:
            tile = self.board.get_tile(row, col)

            if tile is None:
                return "out_of_bounds"

            if tile == TileType.VOID:
                return "void"

            if (
                tile == TileType.FRAGILE
                and state.mode == BlockMode.NORMAL
                and state.orientation == Orientation.STANDING
            ):
                return "standing_on_fragile"

            if tile == TileType.BRIDGE:
                bridge_id = self.board.get_bridge_id(
                    row,
                    col
                )

                if bridge_id is None:
                    raise ValueError(
                        f"Bridge tile at ({row}, {col}) "
                        "has no bridge id."
                    )

                if bridge_id >= len(state.bridges):
                    raise ValueError(
                        f"Bridge id {bridge_id} is out of range "
                        f"for state.bridges={state.bridges}."
                    )

                if state.bridges[bridge_id] is False:
                    return "closed_bridge"

        return None

    
    def is_valid_state(self, state: State) -> bool:
        return self.get_invalid_state_reason(state) is None
    
    
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
    

    def activate_switch(self, switch: dict, bridge_states: list[bool]) -> None:
        """
        Update bridge states according to the switch metadata.

        A normal switch contains:
            bridge_ids
            behavior

        A switch with mixed effects contains:
            effects = [
                {
                    "bridge_ids": [...],
                    "behavior": "open" | "close" | "toggle"
                },
                ...
            ]
        """
        effects = switch.get("effects")

        # Keep compatibility with all existing level JSON files.
        if effects is None:
            effects = [
                {
                    "bridge_ids": switch.get("bridge_ids", []),
                    "behavior": switch.get("behavior", "toggle")
                }
            ]

        for effect in effects:
            behavior = effect.get("behavior", "toggle")
            bridge_ids = effect.get("bridge_ids", [])

            for bridge_id in bridge_ids:
                if bridge_id < 0 or bridge_id >= len(bridge_states):
                    raise ValueError(
                        f"Invalid bridge id in switch: {bridge_id}"
                    )

                if behavior == "toggle":
                    bridge_states[bridge_id] = not bridge_states[bridge_id]

                elif behavior == "open":
                    bridge_states[bridge_id] = True

                elif behavior == "close":
                    bridge_states[bridge_id] = False

                else:
                    raise ValueError(
                        f"Unknown switch behavior: {behavior}"
                    )


    def create_split_move_candidate(
        self,
        state: State,
        direction: str
    ) -> tuple[State, tuple[int, int]] | None:
        """
        Tạo state mà active cube cố di chuyển tới.

        Return:
            (candidate_state, moved_position)

        None:
            Cube cố di chuyển vào đúng ô của cube còn lại.
            Đây là action bị bỏ qua, không phải rơi.
        """
        if state.mode != BlockMode.SPLIT:
            return None

        if state.cube1 is None or state.cube2 is None:
            raise ValueError(
                "Split state must have cube1 and cube2 positions."
            )

        direction = direction.upper()

        if direction not in CUBE_MOVE_DELTAS:
            raise ValueError(
                f"Invalid cube move direction: {direction}"
            )

        dr, dc = CUBE_MOVE_DELTAS[direction]

        cube1 = state.cube1
        cube2 = state.cube2

        if state.active_cube == 1:
            row, col = cube1

            new_cube1 = (
                row + dr,
                col + dc
            )
            new_cube2 = cube2

            if new_cube1 == new_cube2:
                return None

            moved_position = new_cube1

        elif state.active_cube == 2:
            row, col = cube2

            new_cube1 = cube1
            new_cube2 = (
                row + dr,
                col + dc
            )

            if new_cube2 == new_cube1:
                return None

            moved_position = new_cube2

        else:
            raise ValueError(
                f"Invalid active cube: {state.active_cube}"
            )

        candidate_state = State(
            row=state.row,
            col=state.col,
            orientation=state.orientation,
            bridges=state.bridges,
            mode=BlockMode.SPLIT,
            cube1=new_cube1,
            cube2=new_cube2,
            active_cube=state.active_cube
        )

        return candidate_state, moved_position


    def move_active_cube(
        self,
        state: State,
        direction: str
    ) -> State | None:
        candidate_data = self.create_split_move_candidate(
            state,
            direction
        )

        if candidate_data is None:
            return None

        next_state, moved_position = candidate_data

        if not self.is_valid_state(next_state):
            return None

        next_state = self.apply_switches(
            next_state,
            trigger_positions=[moved_position]
        )

        if not self.is_valid_state(next_state):
            return None

        next_state = self.merge_cubes_if_possible(
            next_state
        )

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
    

    def get_move_cost(self, current_state: State, next_state: State, action: str) -> int:
        """
        Compute the non-uniform cost of a valid move.

        Cost design:
        - normal move / soft switch / switch cube: 1
        - standing -> lying transition: 2
        - activating heavy switch while standing: 3
        - moving across fragile tile: 4

        If multiple conditions apply, use the maximum applicable cost.
        """
        action = action.upper()

        # switching control between split cubes is a simple control action.
        if action in {SWITCH_CUBE, "SPACE"}:
            return NORMAL_MOVE_COST

        cost = NORMAL_MOVE_COST

        # Case 1: standing -> lying transition
        # This is riskier because the block occupies two cells after the move
        if (
            current_state.mode == BlockMode.NORMAL
            and current_state.orientation == Orientation.STANDING
            and next_state.mode == BlockMode.NORMAL
            and next_state.orientation in {Orientation.HORIZONTAL, Orientation.VERTICAL}
        ):
            cost = max(cost, STANDIND_TO_LYING_COST)

        # Check the tiles occupied by the next state
        for row, col in get_occupied_tiles(next_state):
            tile = self.board.get_tile(row, col)

            # Case 2: fragile tile
            # Standing on fragile is already invalid, so this only applies
            # to valid states such as lying across fragile or split cube on fragile
            if tile == TileType.FRAGILE:
                cost = max(cost, FRAGILE_TILE_COST)

            # Case 3: heavy switch
            # Heavy switch is only activated by a normal standing block
            if (
                tile == TileType.HEAVY_SWITCH
                and next_state.mode == BlockMode.NORMAL
                and next_state.orientation == Orientation.STANDING
            ):
                cost = max(cost, HEAVY_SWITCH_COST)

        return cost


    def get_successors(self, state: State) -> list[tuple[str, State, int]]:
        successors = []

        actions = list(DIRECTIONS)

        if state.mode == BlockMode.SPLIT:
            actions.append(SWITCH_CUBE)

        for action in actions:
            next_state = self.apply_move(state, action)
            
            if next_state is not None:
                cost = self.get_move_cost(
                    current_state=state,
                    next_state=next_state,
                    action=action
                )
                successors.append((action, next_state, cost))

        return successors
    

    def try_move(self, action: str) -> MoveResult:
        """
        Thực hiện action và trả về kết quả chi tiết.

        Hàm này dành cho GUI chơi thủ công.
        Solver vẫn sử dụng apply_move() và get_successors().
        """
        previous_state = self.state
        normalized_action = action.strip().upper()

        # -----------------------------------------------
        # Đổi active cube
        # -----------------------------------------------
        if normalized_action in {
            SWITCH_CUBE,
            "SPACE"
        }:
            next_state = self.switch_active_cube(
                previous_state
            )

            if next_state is None:
                return MoveResult(
                    status=MoveStatus.IGNORED,
                    previous_state=previous_state,
                    reason="not_in_split_mode"
                )

            self.state = next_state

            return MoveResult(
                status=MoveStatus.MOVED,
                previous_state=previous_state,
                attempted_state=next_state,
                resulting_state=next_state
            )

        # Action không được hỗ trợ.
        if normalized_action not in DIRECTIONS:
            return MoveResult(
                status=MoveStatus.IGNORED,
                previous_state=previous_state,
                reason="unknown_action"
            )

        # -----------------------------------------------
        # Split mode
        # -----------------------------------------------
        if previous_state.mode == BlockMode.SPLIT:
            candidate_data = self.create_split_move_candidate(
                previous_state,
                normalized_action
            )

            # Cube cố đi vào đúng ô của cube còn lại.
            if candidate_data is None:
                return MoveResult(
                    status=MoveStatus.IGNORED,
                    previous_state=previous_state,
                    reason="cube_collision"
                )

            attempted_state, moved_position = (
                candidate_data
            )

            invalid_reason = (
                self.get_invalid_state_reason(
                    attempted_state
                )
            )

            if invalid_reason is not None:
                return MoveResult(
                    status=MoveStatus.LOST,
                    previous_state=previous_state,
                    attempted_state=attempted_state,
                    reason=invalid_reason
                )

            next_state = self.apply_switches(
                attempted_state,
                trigger_positions=[moved_position]
            )

            invalid_reason = (
                self.get_invalid_state_reason(
                    next_state
                )
            )

            if invalid_reason is not None:
                return MoveResult(
                    status=MoveStatus.LOST,
                    previous_state=previous_state,
                    attempted_state=next_state,
                    reason=invalid_reason
                )

            next_state = self.merge_cubes_if_possible(
                next_state
            )

            invalid_reason = (
                self.get_invalid_state_reason(
                    next_state
                )
            )

            if invalid_reason is not None:
                return MoveResult(
                    status=MoveStatus.LOST,
                    previous_state=previous_state,
                    attempted_state=next_state,
                    reason=invalid_reason
                )

        # -----------------------------------------------
        # Normal mode
        # -----------------------------------------------
        else:
            # move_block chỉ tính chuyển động hình học,
            # chưa kiểm tra board.
            attempted_state = move_block(
                previous_state,
                normalized_action
            )

            invalid_reason = (
                self.get_invalid_state_reason(
                    attempted_state
                )
            )

            if invalid_reason is not None:
                return MoveResult(
                    status=MoveStatus.LOST,
                    previous_state=previous_state,
                    attempted_state=attempted_state,
                    reason=invalid_reason
                )

            next_state = self.apply_switches(
                attempted_state
            )

            # Switch có thể vừa đóng bridge dưới block.
            invalid_reason = (
                self.get_invalid_state_reason(
                    next_state
                )
            )

            if invalid_reason is not None:
                return MoveResult(
                    status=MoveStatus.LOST,
                    previous_state=previous_state,
                    attempted_state=next_state,
                    reason=invalid_reason
                )

        # -----------------------------------------------
        # State hợp lệ
        # -----------------------------------------------
        self.state = next_state

        if self.is_goal_state(next_state):
            status = MoveStatus.WON
        else:
            status = MoveStatus.MOVED

        return MoveResult(
            status=status,
            previous_state=previous_state,
            attempted_state=next_state,
            resulting_state=next_state
        )


    def move(self, direction: str) -> bool:
        """
        API tương thích với code cũ.

        True:
            MOVED hoặc WON.

        False:
            IGNORED hoặc LOST.
        """
        result = self.try_move(direction)

        return result.status in {
            MoveStatus.MOVED,
            MoveStatus.WON,
        }
    

    def reset(self):
        self.state = self.initial_state

    
    def is_win(self) -> bool:
        return self.is_goal_state(self.state)
    
    
    def get_occupied_tiles(self):
        return get_occupied_tiles(self.state)