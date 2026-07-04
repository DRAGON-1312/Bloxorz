import heapq
import time
import tracemalloc

from core.level_loader import load_level
from core.game import Game
from core.state import State
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
    raise NotImplementedError("UCS solve() has not been implemented yet.")


if __name__ == "__main__":
    main()