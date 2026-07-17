from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from core.game import Game
from solvers.astar import solve as solve_astar
from solvers.bfs import solve as solve_bfs
from solvers.ids import solve as solve_ids
from solvers.result import SearchResult
from solvers.ucs import solve as solve_ucs

if TYPE_CHECKING:
    from core.board import Board
    from gui.controller import GameController


class SolverAlgorithm(str, Enum):
    """
    Các thuật toán mà GUI cho phép người dùng lựa chọn.

    Kế thừa str giúp giá trị enum dễ dùng với Text/Button của Ursina.
    """
    BFS = "BFS"
    IDS = "IDS"
    UCS = "UCS"
    ASTAR = "A*"


class SolverController:
    """
    Điều phối việc chạy các thuật toán tìm kiếm cho GUI.

    Trách nhiệm:
    - Nhận thuật toán người dùng lựa chọn.
    - Tạo một Game mới từ board hiện tại.
    - Chạy BFS, IDS, UCS hoặc A*.
    - Lưu kết quả gần nhất.
    - Kiểm tra lại đường đi mà solver trả về.

    SolverController không:
    - Thay đổi Game đang được người chơi điều khiển.
    - Tự phát lại lời giải.
    - Tự tạo thành phần giao diện Ursina.
    """

    SUPPORTED_ALGORITHMS = tuple(
        algorithm.value
        for algorithm in SolverAlgorithm
    )


    def __init__(
        self,
        game_controller: GameController,
        ids_max_depth: int = 120
    ) -> None:
        if ids_max_depth < 0:
            raise ValueError(
                "ids_max_depth must be greater than or equal to 0."
            )
        
        self.game_controller = game_controller
        self.ids_max_depth = ids_max_depth

        self.is_solving = False
        self.last_algorithm: SolverAlgorithm | None = None
        self.last_result: SearchResult | None = None


    def solve_current_level(
        self,
        algorithm: SolverAlgorithm | str,
        *,
        ids_max_depth: int | None = None
    ) -> SearchResult:
        """
        Giải level hiện tại từ trạng thái ban đầu.

        Solver luôn dùng một Game mới nên:
        - Không làm thay đổi state mà người chơi đang chơi.
        - Không làm thay đổi move_count.
        - Không ảnh hưởng trạng thái thắng/thua của GUI.
        """
        board = self.game_controller.board

        return self.solve_board(
            board=board,
            algorithm=algorithm,
            ids_max_depth=ids_max_depth
        )
    

    def solve_board(
        self,
        board: Board,
        algorithm: SolverAlgorithm | str,
        *,
        ids_max_depth: int | None = None
    ) -> SearchResult:
        """
        Chạy một thuật toán trên board được truyền vào.

        Hàm này hữu ích cho:
        - GUI hiện tại.
        - Unit test.
        - Chạy thí nghiệm độc lập với giao diện.
        """
        if self.is_solving:
            raise RuntimeError(
                "Another solver is already running."
            )
        
        selected_algorithm = self.normalize_algorithm(
            algorithm
        )

        self.is_solving = True
        self.last_algorithm = None
        self.last_result = None

        try:
            # Mỗi lần solve sử dụng một Game mới để không làm thay đổi
            # game mà người chơi đang điều khiển.
            solver_game = Game(board)

            if selected_algorithm == SolverAlgorithm.BFS:
                result = solve_bfs(solver_game)

            elif selected_algorithm == SolverAlgorithm.IDS:
                max_depth = (
                    self.ids_max_depth
                    if ids_max_depth is None
                    else ids_max_depth
                )

                if max_depth < 0:
                    raise ValueError(
                        "ids_max_depth must be greater than or equal to 0."
                    )
                
                result = solve_ids(
                    solver_game,
                    max_depth=max_depth
                )

            elif selected_algorithm == SolverAlgorithm.UCS:
                result = solve_ucs(solver_game)

            elif selected_algorithm == SolverAlgorithm.ASTAR:
                result = solve_astar(solver_game)

            else:
                raise RuntimeError(
                    f"Unsupported solver algorithm: "
                    f"{selected_algorithm}"
                )
            
            self._validate_result(
                board=board,
                result=result
            )

            self.last_algorithm = selected_algorithm
            self.last_result = result

            return result
        
        finally:
            # [ĐỒNG BỘ HÓA] Thao tác trả quyền (UP / SIGNAL / RELEASE)
            # Khối `finally` luôn chạy kể cả khi thuật toán thành công (return) hoặc bị crash (exception).
            # Đảm bảo unlock trạng thái bận, tránh gây nghẽn (deadlock) cho các lần gọi sau.
            self.is_solving = False


    def clear_last_result(self) -> None:
        """
        Xóa kết quả solver gần nhất.

        Nên gọi khi đổi level nếu SolverPanel vẫn đang hiển thị
        thống kê của level trước.
        """
        self.last_algorithm = None
        self.last_result = None


    @staticmethod
    def normalize_algorithm(
        algorithm: SolverAlgorithm | str
    ) -> SolverAlgorithm:
        """
        Chuyển tên thuật toán người dùng nhập về enum chuẩn.

        Các tên được chấp nhận:
        - BFS
        - IDS
        - UCS
        - A*, ASTAR, A-STAR, A_STAR
        """
        if isinstance(algorithm, SolverAlgorithm):
            return algorithm
        
        normalized_name = algorithm.strip().upper().replace(" ", "")

        aliases = {
            "BFS": SolverAlgorithm.BFS,
            "IDS": SolverAlgorithm.IDS,
            "UCS": SolverAlgorithm.UCS,
            "A*": SolverAlgorithm.ASTAR,
            "ASTAR": SolverAlgorithm.ASTAR,
            "A-STAR": SolverAlgorithm.ASTAR,
            "A_STAR": SolverAlgorithm.ASTAR,
        }

        try:
            return aliases[normalized_name]
        except KeyError as error:
            supported = ", ".join(
                SolverController.SUPPORTED_ALGORITHMS
            )

            raise ValueError(
                f"Unknown solver algorithm: {algorithm!r}. "
                f"Supported algorithms: {supported}."
            ) from error
        

    @staticmethod
    def _validate_result(
        board: Board,
        result: SearchResult
    ) -> None:
        """
        Phát lại lời giải bằng game logic để kiểm tra kết quả solver.

        Việc kiểm tra này không tạo animation và không thay đổi
        GameController của người chơi.
        """
        path = result.path

        if path is None:
            if result.solution_length is not None:
                raise ValueError(
                    "A result without a path must have "
                    "solution_length=None."
                )

            if result.solution_cost is not None:
                raise ValueError(
                    "A result without a path must have "
                    "solution_cost=None."
                )

            return
        
        if result.solution_length != len(path):
            raise ValueError(
                "SearchResult.solution_length does not match "
                f"the actual path length: "
                f"{result.solution_length} != {len(path)}."
            )

        validation_game = Game(board)
        current_state = validation_game.initial_state
        calculated_cost = 0

        for step_number, action in enumerate(
            path,
            start=1
        ):
            next_state = validation_game.apply_move(
                current_state,
                action
            )

            if next_state is None:
                raise ValueError(
                    "Solver returned an invalid path at "
                    f"step {step_number}: action={action!r}."
                )

            calculated_cost += (
                validation_game.get_move_cost(
                    current_state=current_state,
                    next_state=next_state,
                    action=action
                )
            )

            current_state = next_state

        if not validation_game.is_goal_state(
            current_state
        ):
            raise ValueError(
                "Solver path is valid but does not reach the goal."
            )

        if (
            result.solution_cost is not None
            and result.solution_cost != calculated_cost
        ):
            raise ValueError(
                "SearchResult.solution_cost does not match "
                f"the replayed path cost: "
                f"{result.solution_cost} != {calculated_cost}."
            )