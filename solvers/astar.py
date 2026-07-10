import heapq
import time
import tracemalloc
import math

from core.level_loader import load_level
from core.game import Game
from core.state import State, BlockMode
from solvers.result import SearchResult
from solvers.utils import reconstruct_path
from core.block import get_occupied_tiles


LEVEL_PATH = "levels/combined_advanced_levels/stage_09.json"


def main():
    board = load_level(LEVEL_PATH)
    game = Game(board)

    try:
        result = solve(game)
    except NotImplementedError as error:
        print(error)
        return

    print("===== A* Result =====")
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


def heuristic(game: Game, state: State) -> int:
    """
    Admissible heuristic for A*.

    We relax the problem by ignoring:
    - block orientation constraints,
    - fragile risk,
    - bridge open/closed configuration,
    - switch requirements,
    - split/merge requirements.

    The block is approximated by the occupied cell that is closest to the goal.
    Since one roll can move the block by at most about two cells, we divide
    the Manhattan distance by 2 and round up.
    """
    goal_row, goal_col = game.board.goal

    occupied_tiles = get_occupied_tiles(state)

    min_distance = min(
        abs(row - goal_row) + abs(col - goal_col)
        for row, col in occupied_tiles
    )

    return math.ceil(min_distance / 2)


def solve(game: Game) -> SearchResult:
    """
    A* Search.

    f(n) = g(n) + h(n)

    g(n): real cost from the initial state to the current state.
    h(n): heuristic estimate from the current state to the goal.
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    start_state = game.initial_state

    frontier = []
    counter = 0

    start_g = 0
    start_f = start_g + heuristic(game, start_state)

    heapq.heappush(
        frontier, 
        (start_f, start_g, counter, start_state)
    )

    #  best_cost[state] stores the lowest known g(n) cost to reach this state.
    best_cost = {
        start_state: 0
    }

    # parent is used to reconstruct the final path.
    # parent[state] = (previous_state, action)
    parent = {
        start_state: None
    }

    expanded_nodes = 0

    while frontier:
        current_f, current_g, _, current_state = heapq.heappop(frontier)

        # Skip outdated entries in the priority queue.
        # This happens when we later find a cheaper path to the same state.
        if current_g != best_cost[current_state]:
            continue

        # In A*, goal test should be done when the node is popped from frontier.
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
                solution_cost=current_g
            )
        
        # The state is counted as expanded only when its successors are generated.
        expanded_nodes += 1

        for action, next_state, step_cost in game.get_successors(current_state):
            new_g = current_g + step_cost

            # If next_state has never been reached before, or we found a cheaper path.
            if next_state not in best_cost or new_g < best_cost[next_state]:
                best_cost[next_state] = new_g
                parent[next_state] = (current_state, action)

                counter += 1
                new_f = new_g + heuristic(game, next_state)

                heapq.heappush(
                    frontier,
                    (new_f, new_g, counter, next_state)
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