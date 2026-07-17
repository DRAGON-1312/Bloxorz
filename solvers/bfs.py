from collections import deque
import time
import tracemalloc

from core.level_loader import load_level
from core.game import Game
from core.state import State
from solvers.result import SearchResult
from solvers.utils import reconstruct_path, calculate_path_cost


LEVEL_PATH = "levels/combined_advanced_levels/stage_09.json"


def main():
    board = load_level(LEVEL_PATH)
    game = Game(board)

    try:
        result = solve(game)
    except NotImplementedError as error:
        print(error)
        return

    print("===== BFS Result =====")
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
    start_time = time.perf_counter()
    tracemalloc.start()

    start_state = game.initial_state
    
    # Khởi tạo Queue cho BFS và set để lưu các trạng thái đã duyệt
    frontier = deque([start_state])
    reached = {start_state}
    
    # Dictionary để truy vết đường đi
    parent: dict[State, tuple[State, str] | None] = {start_state: None}
    
    expanded_nodes = 0
    goal_state: State | None = None

    try:
        while frontier:
            current_state = frontier.popleft()

            # Nếu tìm thấy đích thì dừng lại ngay
            if game.is_goal_state(current_state):
                goal_state = current_state
                break
                
            expanded_nodes += 1

            # Duyệt qua các trạng thái kế tiếp
            for action, next_state, step_cost in game.get_successors(current_state):
                if next_state not in reached:
                    reached.add(next_state)
                    parent[next_state] = (current_state, action)
                    frontier.append(next_state)

    finally:
        # Chốt thời gian và bộ nhớ dù có tìm thấy đường hay không
        search_time = time.perf_counter() - start_time
        _, memory_usage = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # Xử lý kết quả trả về
    if goal_state is None:
        return SearchResult(
            path=None,
            search_time=search_time,
            memory_usage=memory_usage,
            expanded_nodes=expanded_nodes,
            solution_length=None,
            solution_cost=None
        )

    # Nếu tìm thấy đích, gọi hàm reconstruct_path để lấy danh sách hành động
    path = reconstruct_path(parent, goal_state)

    solution_cost = calculate_path_cost(game, path)

    return SearchResult(
        path=path,
        search_time=search_time,
        memory_usage=memory_usage,
        expanded_nodes=expanded_nodes,
        solution_length=len(path),
        solution_cost=solution_cost
    )


if __name__ == "__main__":
    main()