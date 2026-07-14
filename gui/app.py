from __future__ import annotations

from typing import TYPE_CHECKING

from ursina import Entity, Ursina, Vec3, camera, color, window

from gui.controller import GameController
from gui.input_controller import InputController
from gui.level_manager import LevelManager
from gui.views.block import BlockView
from gui.views.board import BoardView
from gui.views.hud import HUD
from gui.scene import SceneEnvironment

if TYPE_CHECKING:
    from core.board import Board


def main() -> None:
    """
    Entry point của GUI.
    """
    app = BloxorzApp()
    app.run()


class KeyboardHandler(Entity):
    """
    Entity trung gian nhận sự kiện bàn phím từ Ursina.

    Khi người chơi nhấn một phím, Ursina tự động gọi:

        KeyboardHandler.input(key)

    Sau đó KeyboardHandler chuyển phím đó cho InputController.
    """

    def __init__(
        self,
        input_controller: InputController
    ) -> None:
        super().__init__(name="KeyboardHandler")

        self.input_controller = input_controller


    def input(self, key: str) -> None:
        """
        Hàm này được Ursina tự động gọi khi có sự kiện bàn phím.

        Ví dụ:
            Nhấn W     -> key = "w"
            Nhấn Space -> key = "space"
            Nhấn ↑     -> key = "up arrow"

        Khi thả W:
            key = "w up"

        InputController sẽ tự bỏ qua các phím không nằm trong keymap.
        """
        self.input_controller.handle_input(key)


class BloxorzApp:
    """
    Composition root của phần GUI.

    Đây là nơi khởi tạo và kết nối:
    - Ursina.
    - LevelManager.
    - BoardView.
    - BlockView.
    - HUD.
    - GameController.
    - InputController.
    - KeyboardHandler.

    App không chứa luật chơi Bloxorz.
    """
    def __init__(self) -> None:
        # Ursina phải được tạo trước mọi Entity.
        self.ursina_app = Ursina()

        self._configure_window()

        # Tạo nền, ánh sáng và bóng đổ trước khi dựng board.
        self.scene_environment = SceneEnvironment()

        # 1. Load level đầu tiên
        self.level_manager = LevelManager()
        self.board = self.level_manager.load_by_index(0)

        # 2. Tạo các View
        self.board_view = BoardView(self.board)
        self.block_view = BlockView()
        self.hud = HUD()

        # 3. Tạo GameController
        # GameController sẽ:
        # - Tạo Game.
        # - Đồng bộ State với các View.
        # - Kiểm tra thắng.
        # - Đếm số bước.
        self.game_controller = GameController(
            board=self.board,
            board_view=self.board_view,
            block_view=self.block_view,
            hud=self.hud
        )

        # Nối nút Restart trong HUD với controller.
        self.hud.set_restart_callback(
            self.game_controller.restart
        )

        # 4. Tạo InputController
        self.input_controller = InputController(
            game_controller=self.game_controller,
            level_manager=self.level_manager,
            on_level_changed=self._handle_level_changed
        )

        # 5. Nối bàn phím Ursina với InputController
        # KeyboardHandler là một Entity nên Ursina sẽ tự động gọi
        # keyboard_handler.input(key) mỗi khi người dùng nhấn phím.
        self.keyboard_handler = KeyboardHandler(
            input_controller=self.input_controller
        )

        # 6. Đặt camera nhìn vào board
        self._setup_camera()

    
    def _configure_window(self) -> None:
        window.title = "Bloxorz Solver"
        window.borderless = False
        window.fullscreen = False

        window.fps_counter.enabled = False
        window.exit_button.visible = False

        # Tắt các thành phần debug của Ursina.
        entity_counter = getattr(
            window,
            "entity_counter",
            None
        )

        if entity_counter is not None:
            entity_counter.enabled = False

        collider_counter = getattr(
            window,
            "collider_counter",
            None
        )

        if collider_counter is not None:
            collider_counter.enabled = False

        cog_button = getattr(
            window,
            "cog_button",
            None
        )

        if cog_button is not None:
            cog_button.enabled = False


    def _setup_camera(self) -> None:
        board = self.board

        center_x = (board.cols - 1) / 2
        center_z = -(board.rows - 1) / 2

        board_size = max(
            board.cols,
            board.rows * 1.15
        )

        distance = max(
            9.0,
            board_size * 1.28
        )

        camera.orthographic = False

        camera.position = (
            center_x + distance * 0.72,
            distance * 0.88,
            center_z - distance
        )

        camera.look_at(
            Vec3(center_x, 0, center_z)
        )

        camera.fov = 50
        camera.clip_plane_near = 0.1
        camera.clip_plane_far = 1000


    def _handle_level_changed(
        self,
        board: Board
    ) -> None:
        """
        Callback được InputController gọi sau khi nhấn N hoặc P.

        GameController đã load board mới trước khi callback này chạy.
        App chỉ cần:
        - Cập nhật board hiện tại.
        - Đặt lại camera.
        """
        self.board = board
        self._setup_camera()


    def run(self) -> None:
        self.ursina_app.run()


if __name__ == "__main__":
    main()