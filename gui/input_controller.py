from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from core.block import UP, DOWN, LEFT, RIGHT
from core.game import SWITCH_CUBE

if TYPE_CHECKING:
    from core.board import Board
    from gui.controller import GameController
    from gui.level_manager import LevelManager


class InputController:
    """
    Nhận phím từ Ursina và chuyển chúng thành hành động của game.

    Trách nhiệm:
    - W/A/S/D hoặc phím mũi tên: di chuyển block.
    - Space: đổi cube đang điều khiển trong split mode.
    - R: chơi lại level hiện tại.
    - N: chuyển sang level kế tiếp.
    - P: quay lại level trước.
    - Cho phép khóa input khi menu hoặc replay đang hoạt động.

    InputController không:
    - Tự thay đổi Game state.
    - Tự cập nhật BoardView hoặc BlockView.
    - Chứa luật di chuyển của Bloxorz.
    """

    def __init__(
        self,
        game_controller: GameController,
        level_manager: LevelManager | None = None,
        on_level_changed: Callable[[Board], None] | None = None
    ):
        """
        game_controller:
            Controller thực hiện action và cập nhật các View.

        level_manager:
            Dùng để chuyển level bằng phím N/P.

        on_level_changed:
            Callback tùy chọn được gọi sau khi chuyển level.
            App có thể dùng callback này để cập nhật camera.
        """
        self.game_controller = game_controller
        self.level_manager = level_manager

        # Thuộc tính nội bộ dùng để lưu callback khi chuyển level.
        # Khởi tạo bằng None, sau đó gán qua property để setter kiểm tra callback đầu vào.
        self._on_level_changed: Callable[[Board], None] | None = None
        self.on_level_changed = on_level_changed

        # Bật nhận input mặc định; phép gán đi qua setter để kiểm tra kiểu bool.
        self.enabled = True

        self._keymap: dict[str, str] = {
            # Đi lên
            "w": UP,
            "up arrow": UP,

            # Đi xuống
            "s": DOWN,
            "down arrow": DOWN,

            # Sang trái
            "a": LEFT,
            "left arrow": LEFT,

            # Sang phải
            "d": RIGHT,
            "right arrow": RIGHT,

            # Đổi cube đang điều khiển trong split mode
            "space": SWITCH_CUBE,
        }


    def handle_input(self, key: str) -> bool:
        """
        Xử lý một phím do Ursina gửi đến.

        Return:
            True:
                Phím đã được InputController xử lý.

            False:
                Phím không thuộc điều khiển game hoặc input đang bị khóa.
        """
        if not self.enabled:
            return False
        
        # Khóa toàn bộ phím khi animation đang chạy,
        # bao gồm cả R, N và P.
        if self.game_controller.is_animating:
            return False
        
        if not isinstance(key, str):
            return False
        
        normalized_key = key.strip().lower()

        action = self._keymap.get(normalized_key)

        if action is not None:
            return self.game_controller.handle_action(action)
        
        # Restart level hiện tại
        if normalized_key == "r":
            self.game_controller.restart()
            return True
        
        # Chuyển level
        if normalized_key == "n":
            return self.load_next_level()
        
        if normalized_key == "p":
            return self.load_previous_level()
        
        # Các phím khác như chuột, Escape hoặc phím nhả ra
        # sẽ bị bỏ qua.
        return False
    

    def load_next_level(self) -> bool:
        if self.level_manager is None:
            return False

        if not self.level_manager.has_next_level():
            return False

        board = self.level_manager.next_level()

        self.game_controller.load_board(board)
        self._notify_level_changed(board)

        return True
    
    
    def load_previous_level(self) -> bool:
        if self.level_manager is None:
            return False
        
        board = self.level_manager.previous_level()

        self.game_controller.load_board(board)
        self._notify_level_changed(board)

        return True
    

    def _notify_level_changed(self, board: Board) -> None:
        """
        Báo cho App biết board đã thay đổi.

        App có thể dùng callback này để:
        - Cập nhật board hiện tại.
        - Tính lại tâm board.
        - Đặt lại camera.
        """
        callback = self.on_level_changed

        if callback is not None:
            callback(board)


    @property
    def enabled(self) -> bool:
        """
        Cho biết InputController có đang nhận input hay không.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """
        Bật hoặc khóa việc xử lý input.
        """
        if not isinstance(value, bool):
            raise TypeError(
                f"enabled must be bool, got {type(value).__name__}"
            )

        self._enabled = value

    @property
    def on_level_changed(
        self
    ) -> Callable[[Board], None] | None:
        return self._on_level_changed


    @on_level_changed.setter
    def on_level_changed(
        self,
        callback: Callable[[Board], None] | None
    ) -> None:
        if callback is not None and not callable(callback):
            raise TypeError(
                "on_level_changed must be callable or None"
            )

        self._on_level_changed = callback