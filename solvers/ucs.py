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


LEVEL_PATH = "levels/combined_advanced_levels/stage_09.json"


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
    print(f"Solution cost: {result.solution_cost}")

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
    Uniform-Cost Search.

    UCS always expands the state with the lowest path cost g(n).

    g(n): real cost from the initial state to the current state.
    The step cost is provided by game.get_successors().
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    start_state = game.initial_state

    frontier = []
    counter = 0

    # Each item in frontier:
    # (path_cost, counter, state)
    heapq.heappush(
        frontier,
        (0, counter, start_state)
    )

    # best_cost[state] stores the lowest known cost to reach this state.
    best_cost = {
        start_state: 0
    }

    # parent[state] = (previous_state, action)
    parent = {
        start_state: None
    }

    expanded_nodes = 0

    while frontier:
        current_cost, _, current_state = heapq.heappop(frontier)

        # Skip outdated entries.
        # This happens if a cheaper path to the same state was found later.
        if current_cost > best_cost.get(current_state, float("inf")):
            continue

        # In UCS, goal test should be done when the node is popped,
        # because this guarantees the cheapest path to the goal.
        if game.is_goal_state(current_state):
            path = reconstruct_path(parent, current_state)

            search_time = time.perf_counter() - start_time
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            return SearchResult(
                path=path,
                search_time=search_time,
                memory_usage=peak_memory,
                expanded_nodes=expanded_nodes,
                solution_length=len(path),
                solution_cost=current_cost
            )

        # The state is counted as expanded only when its successors are generated.
        expanded_nodes += 1

        for action, next_state, step_cost in game.get_successors(current_state):
            new_cost = current_cost + step_cost

            # If next_state has never been reached before,
            # or this path is cheaper than the previous best path.
            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                parent[next_state] = (current_state, action)

                counter += 1

                heapq.heappush(
                    frontier,
                    (new_cost, counter, next_state)
                )

    # No solution found.
    search_time = time.perf_counter() - start_time
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return SearchResult(
        path=None,
        search_time=search_time,
        memory_usage=peak_memory,
        expanded_nodes=expanded_nodes,
        solution_length=None,
        solution_cost=None
    )


if __name__ == "__main__":
    main()