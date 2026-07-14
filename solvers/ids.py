import time
import tracemalloc

from core.level_loader import load_level
from core.game import Game
from core.state import State
from solvers.result import SearchResult
from solvers.utils import reconstruct_path, calculate_path_cost


LEVEL_PATH = "levels/combined_advanced_levels/stage_08.json"


FOUND = "found"
FAILURE = "failure"
CUTOFF = "cutoff"


def main():
    board = load_level(LEVEL_PATH)
    game = Game(board)

    try:
        result = solve(game)
    except NotImplementedError as error:
        print(error)
        return

    print("===== IDS Result =====")
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


def solve(game: Game, max_depth: int = 120) -> SearchResult:
    """
    Iterative Deepening Search.

    IDS repeatedly performs Depth-Limited Search with limits:
    0, 1, 2, ..., max_depth.
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    total_expanded_nodes = 0

    for depth_limit in range(max_depth + 1):
        iteration_start = time.perf_counter()

        status, path, expanded_nodes = depth_limited_search(
            game,
            depth_limit
        )

        iteration_time = time.perf_counter() - iteration_start
        total_expanded_nodes += expanded_nodes

        # Show progress so the program does not appear frozen.
        # print(
        #     f"[IDS] limit={depth_limit:3d} | "
        #     f"status={status:7s} | "
        #     f"expanded={expanded_nodes:6d} | "
        #     f"time={iteration_time:.4f}s",
        #     flush=True
        # )

        if status == FOUND:
            assert path is not None

            search_time = time.perf_counter() - start_time
            _, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            solution_cost = calculate_path_cost(game, path)

            return SearchResult(
                path=path,
                search_time=search_time,
                memory_usage=peak_memory,
                expanded_nodes=total_expanded_nodes,
                solution_length=len(path),
                solution_cost=solution_cost
            )

        if status == FAILURE:
            search_time = time.perf_counter() - start_time
            _, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            return SearchResult(
                path=None,
                search_time=search_time,
                memory_usage=peak_memory,
                expanded_nodes=total_expanded_nodes,
                solution_length=None,
                solution_cost=None
            )

        # CUTOFF means a solution may exist deeper,
        # so IDS continues with the next depth limit.

    search_time = time.perf_counter() - start_time
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return SearchResult(
        path=None,
        search_time=search_time,
        memory_usage=peak_memory,
        expanded_nodes=total_expanded_nodes,
        solution_length=None,
        solution_cost=None
    )


def depth_limited_search(
    game: Game,
    depth_limit: int
) -> tuple[str, list[str] | None, int]:
    """
    Depth-Limited Search using a LIFO stack.

    best_depth[state] stores the smallest depth at which the state
    has been reached during the current DLS iteration.

    Reaching the same state at a greater or equal depth is unnecessary,
    because the shallower path has at least as much remaining depth.
    """
    start_state = game.initial_state

    # Each item:
    # (state, depth, path)
    frontier = [
        (
            start_state,
            0,
            []
        )
    ]

    # Lowest depth discovered for each state in this DLS iteration.
    best_depth = {
        start_state: 0
    }

    result = FAILURE
    expanded_nodes = 0

    while frontier:
        current_state, depth, path = frontier.pop()

        # Skip an outdated entry if this state was later reached
        # through a shallower path.
        if depth > best_depth.get(current_state, depth):
            continue

        if game.is_goal_state(current_state):
            return FOUND, path, expanded_nodes

        # The node is checked for goal but is not expanded beyond the limit.
        if depth >= depth_limit:
            result = CUTOFF
            continue

        expanded_nodes += 1

        successors = game.get_successors(current_state)

        # Reverse so the first action in the original successor order
        # is explored first by the LIFO stack.
        for action, next_state, cost in reversed(successors):
            next_depth = depth + 1
            previous_depth = best_depth.get(next_state)

            # The same state was already reached at an equal or
            # smaller depth, so this new path cannot provide more
            # remaining search depth.
            if (
                previous_depth is not None
                and previous_depth <= next_depth
            ):
                continue

            best_depth[next_state] = next_depth

            frontier.append(
                (
                    next_state,
                    next_depth,
                    path + [action]
                )
            )

    return result, None, expanded_nodes


if __name__ == "__main__":
    main()