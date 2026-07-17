from __future__ import annotations

from typing import TYPE_CHECKING

from ursina import (
    Entity,
    Ursina,
    Vec3,
    camera,
    lerp,
    time,
    window
)

from gui.controller import GameController
from gui.input_controller import InputController
from gui.level_manager import LevelManager
from gui.views.block import BlockView
from gui.views.board import BoardView
from gui.views.hud import HUD
from gui.scene import SceneEnvironment
from gui.solver_controller import SolverController
from gui.views.solver_panel import SolverPanel
from gui.replay_controller import (
    ReplayController,
    ReplayState
)

from core.state import BlockMode, Orientation
from core.tiles import TileType

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


class CameraFollower(Entity):
    """
    Entity gọi hàm cập nhật camera ở mỗi frame.

    Camera vẫn tập trung chủ yếu vào giữa board,
    nhưng dịch chuyển nhẹ theo vị trí của block.
    """
    
    def __init__(
        self,
        bloxorz_app: BloxorzApp
    ) -> None:
        super().__init__(name="CameraFollower")
        self.bloxorz_app = bloxorz_app

    
    def update(self) -> None:
        """
        Ursina tự động gọi method này ở mỗi frame.
        """
        self.bloxorz_app._update_camera_follow()


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

        # 4. Tạo SolverController
        self.solver_controller = SolverController(
            game_controller=self.game_controller,
            ids_max_depth=120
        )

        # Nối nút Restart trong HUD với controller.
        self.hud.set_restart_callback(
            self.game_controller.restart
        )

        # 5. Tạo InputController
        self.input_controller = InputController(
            game_controller=self.game_controller,
            level_manager=self.level_manager,
            on_level_changed=self._handle_level_changed
        )

        # 6. Tạo SolverPanel
        self.solver_panel = SolverPanel(
            solver_controller=self.solver_controller,
            input_controller=self.input_controller,

            # True để mở panel ngay khi test.
            # Sau này có thể đổi thành False.
            start_open=True
        )

        # 7. Create replay_controller
        self.replay_controller = ReplayController(
            game_controller=self.game_controller,
            input_controller=self.input_controller,

            # Khoảng cách giữa hai bước.
            step_interval=0.38,

            # Chờ nhẹ sau khi restart rồi mới chạy bước đầu.
            initial_delay=0.35,

            on_state_changed=self._handle_replay_state,
            on_error=self._handle_replay_error
        )

        self.solver_panel.set_replay_callback(
            self.replay_controller.toggle
        )

        self.solver_panel.note_text.text = (
            "Click Replay again to stop."
        )

        # 8. Nối bàn phím Ursina với InputController
        # KeyboardHandler là một Entity nên Ursina sẽ tự động gọi
        # keyboard_handler.input(key) mỗi khi người dùng nhấn phím.
        self.keyboard_handler = KeyboardHandler(
            input_controller=self.input_controller
        )

        # 9. Đặt camera nhìn vào board
        self._setup_camera()

        # 10. Cho camera bám nhẹ theo block ở mỗi frame.
        # self.camera_follower = CameraFollower(self)

    
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
        """
        Camera perspective tự thích nghi theo hình dạng map:

        - Tính tâm theo các tile thật sự được hiển thị.
        - Bỏ qua các ô VOID dùng để đệm grid.
        - Map dài ngang sẽ được nhìn xa và chéo hơn.
        - Map vuông hoặc sâu vẫn giữ góc trên cao, dễ quan sát.
        """
        board = self.board

        visible_positions: list[tuple[int, int]] = []

        for row in range(board.rows):
            for col in range(board.cols):
                if board.grid[row][col] != TileType.VOID:
                    visible_positions.append((row, col))

        if not visible_positions:
            raise ValueError(
                f"Board '{board.name}' does not contain any visible tile."
            )

        rows = [row for row, _ in visible_positions]
        cols = [col for _, col in visible_positions]

        min_row = min(rows)
        max_row = max(rows)
        min_col = min(cols)
        max_col = max(cols)

        # Tâm của phần map thật sự được hiển thị.
        center_x = (min_col + max_col) / 2
        center_z = -(min_row + max_row) / 2

        visible_width = max_col - min_col + 1
        visible_depth = max_row - min_row + 1

        board_size = max(
            visible_width,
            visible_depth * 1.25
        )

        # Tỉ lệ hình dạng map.
        aspect_ratio = visible_width / max(visible_depth, 1)

        # wide_factor nằm trong đoạn [0, 1].
        #
        # Map gần vuông:
        #     wide_factor gần 0
        #
        # Map dài ngang như Stage 01:
        #     wide_factor gần 1
        wide_factor = max(
            0.0,
            min(
                1.0,
                (aspect_ratio - 1.4) / 2.2
            )
        )

        # Map dài ngang chỉ cần camera lùi thêm nhẹ.
        # Không nên thay đổi góc nhìn quá mạnh giữa các level.
        distance = max(
            13.0,
            board_size * (
                1.58 + 0.08 * wide_factor
            )
        )

        self.camera_center_x = center_x
        self.camera_center_z = center_z

        # Dịch map nhẹ sang trái để tránh HUD.
        screen_left_shift = min(
            0.25,
            visible_width * 0.018
        )

        self.camera_focus = Vec3(
            center_x + screen_left_shift,
            0,
            center_z
        )

        camera.orthographic = False

        # Góc camera cân bằng:
        #
        # - Có độ chéo trái → phải rõ ràng.
        # - Đủ cao để thấy mặt trên tile.
        # - Đủ thấp để thấy mặt bên và chiều dày tile.
        x_factor = 0.68
        height_factor = 0.82
        z_factor = 1.12

        self.camera_offset_x = (
            distance * x_factor
        )

        self.camera_height = (
            distance * height_factor
        )

        self.camera_offset_z = (
            distance * z_factor
        )

        camera.position = Vec3(
            self.camera_focus.x
            - self.camera_offset_x,

            self.camera_height,

            self.camera_focus.z
            - self.camera_offset_z
        )

        camera.look_at(
            self.camera_focus
        )

        # Chỉ tăng FOV rất nhẹ cho map dài.
        # Tránh FOV quá lớn làm hình bị bẹt và méo.
        camera.fov = (
            38
            + 1.0 * wide_factor
        )

        camera.clip_plane_near = 0.1
        camera.clip_plane_far = 1000


    def _get_block_center(self) -> tuple[float, float]:
        """
        Trả về tâm của block trên mặt phẳng XZ.

        Return:
            (world_x, world_z)
        """
        state = self.game_controller.game.state

        if state.mode == BlockMode.NORMAL:
            if state.orientation == Orientation.STANDING:
                block_x = float(state.col)
                block_z = float(-state.row)

            elif state.orientation == Orientation.HORIZONTAL:
                # Block chiếm:
                # (row, col) và (row, col + 1)
                block_x = float(state.col) + 0.5
                block_z = float(-state.row)

            elif state.orientation == Orientation.VERTICAL:
                # Block chiếm:
                # (row, col) và (row + 1, col)
                block_x = float(state.col)
                block_z = -(float(state.row) + 0.5)

            else:
                raise ValueError(
                    f"Unsupported orientation: "
                    f"{state.orientation}"
                )

            return block_x, block_z

        if state.mode == BlockMode.SPLIT:
            if state.cube1 is None or state.cube2 is None:
                raise ValueError(
                    "Split state requires cube1 and cube2."
                )

            cube_1_row, cube_1_col = state.cube1
            cube_2_row, cube_2_col = state.cube2

            # Camera nhìn vào trung điểm của hai cube.
            block_x = (
                cube_1_col + cube_2_col
            ) / 2

            block_z = -(
                cube_1_row + cube_2_row
            ) / 2

            return float(block_x), float(block_z)

        raise ValueError(
            f"Unsupported block mode: {state.mode}"
        )
    

    def _update_camera_follow(self) -> None:
        """
        Cập nhật camera ở mỗi frame.

        Trọng tâm camera:
            85% tâm board
            15% tâm block

        Nhờ vậy:
        - Toàn bộ board vẫn được nhìn thấy.
        - Camera chỉ dịch chuyển nhẹ theo block.
        - Chuyển động được làm mượt bằng lerp.
        """
        if not hasattr(self, "game_controller"):
            return

        # Sau này khi mở menu và ẩn board,
        # camera không cần tiếp tục follow.
        if not self.board_view.root.enabled:
            return
        
        # Giữ camera đứng yên trong lúc block hoặc tile đang phát animation.
        if self.game_controller.is_animating:
            return

        block_x, block_z = self._get_block_center()

        board_weight = 0.85
        block_weight = 0.15

        target_focus = Vec3(
            self.camera_center_x * board_weight
            + block_x * block_weight,

            0,

            self.camera_center_z * board_weight
            + block_z * block_weight
        )

        # Giới hạn blend tối đa bằng 1 để tránh giật
        # nếu có một frame bị chậm bất thường.
        blend = min(
            time.dt * 1.8,
            1.0
        )

        # Làm mượt điểm camera đang nhìn.
        self.camera_focus = lerp(
            self.camera_focus,
            target_focus,
            blend
        )

        desired_position = Vec3(
            self.camera_focus.x + self.camera_offset_x,
            self.camera_height,
            self.camera_focus.z - self.camera_offset_z
        )

        # Làm mượt vị trí camera.
        camera.position = lerp(
            camera.position,
            desired_position,
            blend
        )

        camera.look_at(self.camera_focus)


    def _handle_replay_state(
        self,
        state: ReplayState,
        current_step: int,
        total_steps: int
    ) -> None:
        """
        Đồng bộ trạng thái replay với SolverPanel.
        """
        is_active = state in {
            ReplayState.RUNNING,
            ReplayState.PAUSED
        }

        # Khi đang replay, nút Replay trở thành Stop.
        self.solver_panel.replay_button.text = (
            "Stop"
            if is_active
            else "Replay"
        )

        # Không cho chạy solver khác trong lúc replay.
        self.solver_panel.solve_button.enabled = (
            not is_active
        )

        for button in (
            self.solver_panel.algorithm_buttons.values()
        ):
            button.enabled = not is_active

        if state == ReplayState.RUNNING:
            self.solver_panel._show_status(
                (
                    "Status: Replaying "
                    f"{current_step}/{total_steps}"
                ),
                self.solver_panel.WARNING_COLOR
            )

        elif state == ReplayState.PAUSED:
            self.solver_panel._show_status(
                (
                    "Status: Paused "
                    f"{current_step}/{total_steps}"
                ),
                self.solver_panel.WARNING_COLOR
            )

        else:
            replay_completed = (
                total_steps > 0
                and current_step == total_steps
                and self.game_controller.game.is_win()
            )

            if replay_completed:
                self.solver_panel._show_status(
                    "Status: Replay completed",
                    self.solver_panel.SUCCESS_COLOR
                )
            else:
                self.solver_panel._show_status(
                    "Status: Replay stopped",
                    self.solver_panel.WARNING_COLOR
                )


    def _handle_replay_error(
        self,
        error: Exception
    ) -> None:
        """
        Hiển thị lỗi replay mà không làm crash Ursina.
        """
        self.solver_panel._show_status(
            f"Replay error: {error}",
            self.solver_panel.ERROR_COLOR
        )


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
        # Bảo đảm replay cũ đã dừng.
        self.replay_controller.stop()

        self.board = board

        # Xóa path và statistics của level trước.
        self.solver_panel.clear_result()

        # Tính lại camera theo level mới.
        self._setup_camera()


    def run(self) -> None:
        self.ursina_app.run()


if __name__ == "__main__":
    main()