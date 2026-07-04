import heapq
import time
import tracemalloc

from core.level_loader import load_level
from core.game import Game
from core.state import State, BlockMode
from solvers.result import SearchResult
from solvers.utils import reconstruct_path


LEVEL_PATH = "levels/basic levels/stage_01.json"


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

    if result.path is not None:
        for action in result.path:
            moved = game.move(action)

            if not moved:
                print(f"Invalid action during replay: {action}")
                return

        print(f"Replay win: {game.is_win()}")

    else:
        print("No solution found.")


def heuristic(game: Game, state: State) -> float:
    """
    TODO:
    Implement heuristic function for A*.

    A simple starting idea:
    - Use Manhattan distance from the block position to the goal.
    - Divide by 2 because one roll can move the block by up to 2 cells.
    - Add a small orientation-aware term if needed.

    Important:
    - The heuristic should be admissible if you want to discuss optimality.
    """
    raise NotImplementedError("A* heuristic() has not been implemented yet.")


def solve(game: Game) -> SearchResult:
    """
    TODO:
    Implement A* Search.

    Notes:
    - Use a priority queue with heapq.
    - Priority should be:
        f(n) = g(n) + h(n)
    - g(n) is the path cost from start to current state.
    - h(n) is the heuristic estimate to the goal.
    - Keep best_cost[state] to avoid revisiting worse paths.

    Expected return:
        SearchResult(
            path=...,
            search_time=...,
            memory_usage=...,
            expanded_nodes=...,
            solution_length=...
        )
    """
    raise NotImplementedError("A* solve() has not been implemented yet.")


if __name__ == "__main__":
    main()