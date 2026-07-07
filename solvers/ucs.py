import heapq
import time
import tracemalloc
from itertools import count

from core.level_loader import load_level
from core.game import Game
from core.state import State, Orientation
from core.tiles import TileType
from solvers.result import SearchResult
from solvers.utils import reconstruct_path


LEVEL_PATH = "levels/basic_levels/stage_01.json"


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
    start_time = time.perf_counter()
    tracemalloc.start()

    frontier: list[tuple[int, int, State]] = []
    tie_breaker = count()

    start_state = game.state
    heapq.heappush(frontier, (0, next(tie_breaker), start_state))

    best_cost: dict[State, int] = {start_state: 0}
    parent: dict[State, tuple[State, str] | None] = {start_state: None}

    expanded_nodes = 0
    goal_state: State | None = None

    try:
        while frontier:
            current_cost, _, current_state = heapq.heappop(frontier)

            if current_cost > best_cost.get(current_state, float("inf")):
                continue

            expanded_nodes += 1

            if game.is_goal_state(current_state):
                goal_state = current_state
                break

            for action, next_state, step_cost in game.get_successors(current_state):
                new_cost = current_cost + step_cost

                if new_cost < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = new_cost
                    parent[next_state] = (current_state, action)
                    heapq.heappush(
                        frontier,
                        (new_cost, next(tie_breaker), next_state)
                    )

    finally:
        search_time = time.perf_counter() - start_time
        _, memory_usage = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    if goal_state is None:
        return SearchResult(
            path=None,
            search_time=search_time,
            memory_usage=memory_usage,
            expanded_nodes=expanded_nodes,
            solution_length=None,
        )

    path = reconstruct_path(parent, goal_state)

    return SearchResult(
        path=path,
        search_time=search_time,
        memory_usage=memory_usage,
        expanded_nodes=expanded_nodes,
        solution_length=len(path),
    )

            
    
    
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