from __future__ import annotations
from typing import TYPE_CHECKING

from core.game import Game
from core.move_result import MoveStatus


if TYPE_CHECKING:
    from core.board import Board
    from gui.views.board import BoardView
    from gui.views.block import BlockView
    from gui.views.hud import HUD


class GameController:
    """
    Điều phối giữa game logic và phần hiển thị GUI.

    Trách nhiệm:
    - Giữ đối tượng Game hiện tại.
    - Nhận action từ InputController.
    - Gọi game.try_move(action).
    - Cập nhật BoardView và BlockView.
    - Đếm số lần di chuyển.
    - Kiểm tra trạng thái chiến thắng.
    - Restart hoặc load board mới.

    GameController không:
    - Đọc trực tiếp bàn phím.
    - Tự tạo Entity của Ursina.
    - Chạy BFS, IDS, UCS hoặc A*.
    """

    def __init__(
        self,
        board: Board,
        board_view: BoardView,
        block_view: BlockView,
        hud: HUD | None = None
    ):
        # Các View được truyền từ App.
        self.board_view = board_view
        self.block_view = block_view
        self.hud = hud

        # Board và Game sẽ được khởi tạo trong load_board().
        self.board: Board
        self.game: Game

        self.move_count = 0
        self.is_finished = False
        self.is_animating = False

        self.load_board(board)


    def handle_action(self, action: str) -> bool:
        """
        Thực hiện action và xử lý đầy đủ:
        IGNORED, MOVED, WON hoặc LOST.
        """
        if self.is_finished:
            return False

        result = self.game.try_move(action)

        if result.status == MoveStatus.IGNORED:
            return False

        # Action được tính là một bước kể cả khi người chơi rơi.
        self.move_count += 1

        if result.status == MoveStatus.MOVED:
            self.refresh_views()
            return True

        if result.status == MoveStatus.WON:
            self.is_finished = True
            self.refresh_views()

            if self.hud is not None:
                self.hud.show_message(
                    "You win!\nPress N for next level"
                )

            return True

        if result.status == MoveStatus.LOST:
            self.is_finished = True
            self.is_animating = True

            # Cập nhật số bước trước khi phát animation rơi.
            if self.hud is not None:
                self.hud.update(
                    board=self.board,
                    state=result.previous_state,
                    move_count=self.move_count,
                    is_finished=False
                )

            attempted_state = result.attempted_state

            if attempted_state is None:
                self._finish_loss()

            elif result.reason == "standing_on_fragile":
                # Trước tiên đặt block đứng trên fragile tile
                # để người chơi thấy nguyên nhân tile bị vỡ.
                self.block_view.update(attempted_state)

                def start_block_fall() -> None:
                    """
                    Được gọi sau khi fragile tile đã vỡ hoàn toàn.
                    """
                    self.block_view.play_fall(
                        attempted_state=attempted_state,
                        on_complete=self._finish_loss
                    )

                self.board_view.play_fragile_break(
                    row=attempted_state.row,
                    col=attempted_state.col,
                    on_complete=start_block_fall
                )

            else:
                # Các trường hợp khác:
                # - Ra ngoài board.
                # - Đi vào VOID.
                # - Đi lên bridge đang đóng.
                self.block_view.play_fall(
                    attempted_state=attempted_state,
                    on_complete=self._finish_loss
                )

            return True

        raise RuntimeError(
            f"Unsupported move status: {result.status}"
        )
    

    def restart(self) -> None:
        """
        Khởi động lại level hiện tại.

        Không cho restart trong khi animation vẫn đang chạy.
        """
        if self.is_animating:
            return

        self.game = Game(self.board)
        self.move_count = 0
        self.is_finished = False
        self.is_animating = False

        # Khôi phục fragile tile từng bị vỡ.
        self.board_view.reset_fragile_tiles()

        if self.hud is not None:
            self.hud.clear_message()

        self.refresh_views()
    

    def load_board(self, board: Board) -> None:
        """
        Load một board mới.

        Hàm này được dùng khi:
        - Khởi động game.
        - Chuyển level.
        - Chọn level từ menu.
        """
        self.board = board
        self.game = Game(board)

        self.move_count = 0
        self.is_finished = False
        self.is_animating = False

        # BoardView phải xây lại các tile cho level mới.
        self.board_view.load_board(board)

        if self.hud is not None:
            self.hud.show_message("")

        self.refresh_views()


    def refresh_views(self) -> None:
        """
        Đồng bộ GUI với Game state hiện tại.
        """
        state = self.game.state

        # Cập nhật bridge theo state.bridges.
        self.board_view.update(state)

        # Cập nhật vị trí, orientation hoặc split cubes.
        self.block_view.update(state)

        if self.hud is not None:
            self.hud.update(
                board=self.board,
                state=state,
                move_count=self.move_count,
                is_finished=self.is_finished
            )


    def _finish_loss(self) -> None:
        """
        Kết thúc trạng thái animation rơi và cập nhật HUD.
        """
        self.is_animating = False

        if self.hud is not None:
            self.hud.show_failed_status()
            self.hud.show_message(
                "You lose!\nPress R to restart"
            )