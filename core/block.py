from core.state import State, Orientation, BlockMode


# Valid movement directions 
UP = "UP"
DOWN = "DOWN"
LEFT = "LEFT"
RIGHT = "RIGHT"


DIRECTIONS = [UP, DOWN, LEFT, RIGHT]


def get_occupied_tiles(state: State) -> list[tuple[int, int]]:
    # Case 1: The block is split into two 1x1x1 cubes.
    # In split mode, the occupied cells are cube1 and cube2.
    if state.mode == BlockMode.SPLIT:
        if state.cube1 is None or state.cube2 is None:
            raise ValueError("Split state must have cube1 and cube2 positions")

        return [state.cube1, state.cube2]
    
    # Case 2: Normal 1x1x2 block.
    row, col, orientation = state.row, state.col, state.orientation

    if orientation == Orientation.STANDING:
        return [(row, col)]
    
    elif orientation == Orientation.HORIZONTAL:
        return [(row, col), (row, col + 1)]
    
    elif orientation == Orientation.VERTICAL:
        return [(row, col), (row + 1, col)]
    
    raise ValueError(f"Unknown orientation: {orientation}")


def move_block(state: State, direction: str) -> State:
    direction = direction.upper()

    if direction not in DIRECTIONS:
        raise ValueError(f"Invalid direction: {direction}")
    
    row, col, orientation = state.row, state.col, state.orientation

    # Case 1: The block is standing upright (đứng thẳng)
    if orientation == Orientation.STANDING:
        if direction == UP:
            return State (
                row = row - 2,
                col = col,
                orientation = Orientation.VERTICAL,
                bridges = state.bridges
            )
        
        elif direction == DOWN:
            return State (
                row = row + 1,
                col = col,
                orientation = Orientation.VERTICAL,
                bridges = state.bridges
            )
        
        elif direction == LEFT:
            return State (
                row = row,
                col = col - 2,
                orientation = Orientation.HORIZONTAL,
                bridges = state.bridges
            )
        
        else: # RIGHT
            return State (
                row = row,
                col = col + 1,
                orientation = Orientation.HORIZONTAL,
                bridges = state.bridges
            )
        
    
    # Case 2: The block is lying horizontally (nằm ngang)
    elif orientation == Orientation.HORIZONTAL:
        if direction == UP:
            return State (
                row = row - 1,
                col = col,
                orientation = Orientation.HORIZONTAL,
                bridges = state.bridges
            )
        
        elif direction == DOWN:
            return State (
                row = row + 1,
                col = col,
                orientation = Orientation.HORIZONTAL,
                bridges = state.bridges
            )
        
        elif direction == LEFT:
            return State (
                row = row,
                col = col - 1,
                orientation = Orientation.STANDING,
                bridges = state.bridges
            )
        
        else: # RIGHT
            return State (
                row = row,
                col = col + 2,
                orientation = Orientation.STANDING,
                bridges = state.bridges
            )
    
    # Case 3: The block is lying vertically (nằm dọc)
    elif orientation == Orientation.VERTICAL:
        if direction == UP:
            return State (
                row = row - 1,
                col = col,
                orientation = Orientation.STANDING,
                bridges = state.bridges
            )
        
        elif direction == DOWN:
            return State (
                row = row + 2,
                col = col,
                orientation = Orientation.STANDING,
                bridges = state.bridges
            )
        
        elif direction == LEFT:
            return State (
                row = row,
                col = col - 1,
                orientation = Orientation.VERTICAL,
                bridges = state.bridges
            )
        
        else: # RIGHT
            return State (
                row = row,
                col = col + 1,
                orientation = Orientation.VERTICAL,
                bridges = state.bridges
            )
    
    raise ValueError(f"Unknown orientation: {orientation}")