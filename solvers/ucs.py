import heapq
import time
import tracemalloc

from core.level_loader import load_level
from core.game import Game
from core.state import State, Orientation
from solvers.result import SearchResult
from solvers.utils import reconstruct_path
from core.tiles import TileType


LEVEL_PATH = "levels/basic levels/stage_01.json"


def main():
    board = load_level(LEVEL_PATH)
    game = Game(board)

    try:
        result = solve(game)
    except NotImplementedError as error:
        print(error)
        return

    print("===== UCS Result =====")
    print(f"Level: {board.name}")
    print(f"Path: {result.path}")
    print(f"Search time: {result.search_time:.6f} seconds")
    print(f"Memory usage: {result.memory_usage / 1024:.2f} KB")
    print(f"Expanded nodes: {result.expanded_nodes}")
    print(f"Solution length: {result.solution_length}")

    if result.path is not None:
        for action in result.path:
            moved = game.move(action)

            if not moved:
                print(f"Invalid action during replay: {action}")
                return

        print(f"Replay win: {game.is_win()}")

    else:
        print("No solution found.")


def solve(game: Game) -> SearchResult:
    """
    TODO:
    Implement Uniform-Cost Search.

    Notes:
    - Use a priority queue with heapq.
    - The priority should be the path cost g(n).
    - If every move has cost 1, UCS behaves like BFS.
    - For the report, define and justify the cost function.

    Expected return:
        SearchResult(
            path=...,
            search_time=...,
            memory_usage=...,
            expanded_nodes=...,
            solution_length=...
        )
    """
    
    
def cost(current: Game, reaching:Game) -> int:
    move_cost = 1
    
    # standing to lying, occupies more tiles, cost +1
    if (
        current.state.orientation == Orientation.STANDING
        and (
            reaching.state.orientation == Orientation.VERTICAL
            or reaching.state.orientation == Orientation.HORIZONTAL
        )
    ): move_cost += 1
    
    # touch a fragile tile, dangerous, cost +3
    for coordinate in reaching.get_occupied_tiles():
        if reaching.board.get_tile(coordinate[0],coordinate[1]) == TileType.FRAGILE:
            move_cost += 3
            break
    
    # standing on a heavy switch, cost +2
    if reaching.state.orientation == Orientation.STANDING:
        occupied_coordinate = reaching.get_occupied_tiles()
        if reaching.board.get_tile(occupied_coordinate[0], occupied_coordinate[1]) == "heavy_switch":
            move_cost += 2
    
    return move_cost


if __name__ == "__main__":
    main()