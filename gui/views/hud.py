from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ursina import Button, Entity, Text, camera, color

if TYPE_CHECKING:
    from core.board import Board
    from core.state import State


class HUD:
    """
    Hiển thị thông tin của game trên màn hình.

    Trách nhiệm:
    - Hiển thị tên level.
    - Hiển thị số bước đã đi.
    - Hiển thị mode và orientation của block.
    - Hiển thị cube đang active trong split mode.
    - Hiển thị trạng thái Playing/Completed.
    - Hiển thị thông báo, ví dụ "You win!".
    - Cung cấp nút Restart.

    HUD chỉ là View:
    - Không gọi game.move().
    - Không tự restart Game.
    - Không thay đổi State.
    """

    def __init__(
        self,
        on_restart: Callable[[], None] | None = None
    ):
        """
        on_restart:
            Hàm được gọi khi người chơi bấm nút Restart.

        Ví dụ sau này trong app.py:

            hud = HUD(
                on_restart=game_controller.restart
            )
        """
        self.on_restart = on_restart

        # Root chứa toàn bộ thành phần UI của HUD.
        #
        # camera.ui giúp Entity được vẽ cố định trên màn hình,
        # không bị ảnh hưởng bởi camera 3D.
        self.root = Entity(
            parent=camera.ui,
            name="HUDRoot"
        )

        # Nền mờ phía sau phần thông tin bên trái.
        self.info_panel = Entity(
            parent=self.root,
            name="HUDInfoPanel",
            model="quad",
            texture="white_cube",
            position=(-0.60, 0.38),
            scale=(0.34, 0.22),
            color=color.rgba32(18, 20, 26, 210)
        )

        # Tên level.
        self.level_text = Text(
            parent=self.root,
            name="LevelText",
            text="Level: --",
            position=(-0.75, 0.46),
            origin=(-0.5, 0.5),
            scale=0.85,
            color=color.rgb32(245, 245, 245)
        )

        # Số bước người chơi đã thực hiện.
        self.move_text = Text(
            parent=self.root,
            name="MoveText",
            text="Moves: 0",
            position=(-0.75, 0.42),
            origin=(-0.5, 0.5),
            scale=0.80,
            color=color.rgb32(220, 225, 235)
        )

        # Mode hiện tại: NORMAL hoặc SPLIT.
        self.mode_text = Text(
            parent=self.root,
            name="ModeText",
            text="Mode: NORMAL",
            position=(-0.75, 0.38),
            origin=(-0.5, 0.5),
            scale=0.80,
            color=color.rgb32(220, 225, 235)
        )

        # Orientation khi block ở normal mode.
        self.orientation_text = Text(
            parent=self.root,
            name="OrientationText",
            text="Orientation: STANDING",
            position=(-0.75, 0.34),
            origin=(-0.5, 0.5),
            scale=0.80,
            color=color.rgb32(220, 225, 235)
        )

        # Cube đang được điều khiển khi ở split mode.
        # Khi block ở normal mode, dòng này sẽ được ẩn.
        self.active_cube_text = Text(
            parent=self.root,
            name="ActiveCubeText",
            text="Active cube: 1",
            position=(-0.75, 0.30),
            origin=(-0.5, 0.5),
            scale=0.80,
            color=color.rgb32(255, 210, 80),
            enabled=False
        )

        # Trạng thái game.
        self.status_text = Text(
            parent=self.root,
            name="StatusText",
            text="Status: Playing",
            position=(-0.75, 0.26),
            origin=(-0.5, 0.5),
            scale=0.80,
            color=color.rgb32(130, 220, 150)
        )

        # Thông báo lớn ở giữa phía trên màn hình.
        self.message_text = Text(
            parent=self.root,
            name="MessageText",
            text="",
            position=(0, 0.40),
            origin=(0, 0),
            scale=2.0,
            color=color.rgb32(255, 220, 80),
            enabled=False
        )

        # Nút restart ở góc dưới bên trái.
        self.restart_button = Button(
            parent=self.root,
            name="RestartButton",
            text="Restart [R]",
            position=(-0.67, -0.45),
            scale=(0.17, 0.055),
            color=color.rgb32(55, 70, 90),
            highlight_color=color.rgb32(80, 105, 135),
            pressed_color=color.rgb32(40, 50, 70),
            text_color=color.white,
            on_click=self._handle_restart
        )

    def update(
        self,
        board: Board,
        state: State,
        move_count: int,
        is_finished: bool
    ) -> None:
        """
        Cập nhật toàn bộ thông tin HUD theo game state hiện tại.

        Hàm này được GameController gọi sau mỗi lần:
        - Move thành công.
        - Restart.
        - Load level mới.
        - Trạng thái bridge/split thay đổi.
        """
        self.level_text.text = f"Level: {board.name}"
        self.move_text.text = f"Moves: {move_count}"

        mode_name = self._get_enum_name(state.mode)
        self.mode_text.text = f"Mode: {mode_name}"

        if mode_name == "NORMAL":
            self._show_normal_state(state)
        elif mode_name == "SPLIT":
            self._show_split_state(state)
        else:
            self.orientation_text.text = "Orientation: Unknown"
            self.orientation_text.enabled = True
            self.active_cube_text.enabled = False

        if is_finished:
            self.status_text.text = "Status: Completed"
            self.status_text.color = color.rgb32(255, 215, 80)
        else:
            self.status_text.text = "Status: Playing"
            self.status_text.color = color.rgb32(130, 220, 150)

    def _show_normal_state(self, state: State) -> None:
        """
        Cập nhật HUD khi block đang ở normal mode.
        """
        orientation_name = self._get_enum_name(
            state.orientation
        )

        self.orientation_text.text = (
            f"Orientation: {orientation_name}"
        )
        self.orientation_text.enabled = True

        # Normal mode không có active cube.
        self.active_cube_text.enabled = False

    def _show_split_state(self, state: State) -> None:
        """
        Cập nhật HUD khi block đang được tách thành hai cube.
        """
        # Split mode không có orientation dạng đứng/ngang/dọc.
        self.orientation_text.enabled = False
        self.active_cube_text.enabled = True

        active_cube = state.active_cube

        if active_cube not in {1, 2}:
            raise ValueError(
                f"active_cube must be 1 or 2, got: {active_cube}"
            )

        displayed_cube = active_cube

        self.active_cube_text.text = (
            f"Active cube: {displayed_cube}"
        )

    def show_message(
        self,
        message: str,
        message_color=None
    ) -> None:
        """
        Hiển thị thông báo ở giữa phía trên màn hình.

        Ví dụ:
            hud.show_message("You win!")
            hud.show_message("Invalid move")
            hud.show_message("No solution found")
        """
        self.message_text.text = message
        self.message_text.enabled = bool(message)

        if message_color is None:
            self.message_text.color = color.rgb32(
                255,
                220,
                80
            )
        else:
            self.message_text.color = message_color

    def show_failed_status(self) -> None:
        """
        Hiển thị trạng thái thua sau khi animation rơi kết thúc.
        """
        self.status_text.text = "Status: Failed"
        self.status_text.color = color.rgb32(
            230,
            90,
            90
        )

    def clear_message(self) -> None:
        """
        Xóa thông báo hiện tại.
        """
        self.message_text.text = ""
        self.message_text.enabled = False

    def set_restart_callback(
        self,
        callback: Callable[[], None] | None
    ) -> None:
        """
        Gán hoặc thay đổi hàm được gọi khi nhấn Restart.

        Hàm này hữu ích vì lúc tạo HUD, GameController có thể
        chưa được khởi tạo.
        """
        self.on_restart = callback

    def _handle_restart(self) -> None:
        """
        Được Ursina gọi khi người chơi nhấn nút Restart.
        """
        if self.on_restart is not None:
            self.on_restart()


    def set_visible(self, is_visible: bool) -> None:
        """
        Ẩn hoặc hiện toàn bộ HUD.

        Sau này dùng khi:
        - Đang ở main menu.
        - Chuyển scene.
        - Hiển thị màn hình loading.
        """
        self.root.enabled = is_visible

    @staticmethod
    def _get_enum_name(value) -> str:
        """
        Chuyển Enum thành tên dễ hiển thị.

        Ví dụ:
            BlockMode.NORMAL      -> "NORMAL"
            Orientation.STANDING  -> "STANDING"
        """
        enum_name = getattr(value, "name", None)

        if enum_name is not None:
            return str(enum_name).upper()

        enum_value = getattr(value, "value", value)

        return str(enum_value).split(".")[-1].upper()