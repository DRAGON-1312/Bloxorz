from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from panda3d.core import Quat
from ursina import Entity, Vec3, color, curve, destroy, invoke, time
from ursina.shaders import lit_with_shadows_shader

from core.block import UP, DOWN, LEFT, RIGHT
from core.game import SWITCH_CUBE

if TYPE_CHECKING:
    from core.state import State


class _PhysicalRollDriver(Entity):
    """
    Lăn block bằng một pivot Entity thật.

    Block được gắn tạm vào pivot đặt trên cạnh tiếp xúc. Mỗi frame chỉ
    xoay pivot, nên Ursina áp dụng cùng một transform cho cả:
    - vị trí tâm block;
    - orientation của model.

    Cách này tránh lỗi ở HORIZONTAL -> HORIZONTAL, nơi code cũ:
    - tự tính position bằng rotation_delta.xform();
    - tự ghép quaternion bằng rotation_delta * start_quaternion.

    Hai phép đó không tạo ra cùng hệ trục hiển thị trong trường hợp
    block đã có rotation canonical (0, 0, 90).
    """

    def __init__(
        self,
        rig: Entity,
        start_position: Vec3,
        target_position: Vec3,
        pivot_position: Vec3,
        axis: Vec3,
        duration: float,
        on_complete: Callable[[], None]
    ) -> None:
        super().__init__(
            name="PhysicalRollDriver"
        )

        if duration <= 0:
            raise ValueError(
                "duration must be greater than 0."
            )

        self.rig = rig
        self.original_parent = rig.parent

        self.start_position = Vec3(
            start_position
        )
        self.target_position = Vec3(
            target_position
        )
        self.pivot_position = Vec3(
            pivot_position
        )
        self.axis = Vec3(
            axis
        )

        self.duration = float(
            duration
        )
        self.on_complete = on_complete

        self.start_offset = (
            self.start_position
            - self.pivot_position
        )

        self.final_angle = (
            self._choose_matching_angle()
        )

        # Pivot có cùng parent với block nên pivot_position đang ở đúng
        # hệ tọa độ của BlockRoot.
        self.pivot = Entity(
            parent=self.original_parent,
            name="PhysicalRollPivot",
            position=self.pivot_position
        )

        # world_parent giữ nguyên world transform của block khi đổi parent.
        # Đây cũng là cách Ursina dùng trong ví dụ Rubik's Cube chính thức.
        self.rig.world_parent = (
            self.pivot
        )

        self.elapsed = 0.0
        self._completed = False


    def update(self) -> None:
        if self._completed:
            return

        self.elapsed += time.dt

        progress = min(
            self.elapsed / self.duration,
            1.0
        )

        current_angle = (
            self.final_angle * progress
        )

        rotation_delta = Quat()
        rotation_delta.setFromAxisAngle(
            current_angle,
            self.axis
        )

        # Chỉ xoay pivot. Position và rotation của block được scene graph
        # biến đổi cùng lúc quanh đúng cạnh tiếp xúc.
        self.pivot.quaternion = (
            rotation_delta
        )

        if progress >= 1.0:
            self._completed = True

            # Đưa block ra khỏi pivot nhưng giữ nguyên world transform vừa
            # chạm đất, sau đó hiệu chỉnh sai số vị trí rất nhỏ.
            self.rig.world_parent = (
                self.original_parent
            )

            self.rig.position = (
                self.target_position
            )

            callback = self.on_complete

            invoke(
                callback,
                delay=0.015
            )

            invoke(
                destroy,
                self.pivot,
                delay=0.02
            )

            invoke(
                destroy,
                self,
                delay=0.02
            )


    def _choose_matching_angle(self) -> float:
        """
        Chọn +90 hoặc -90 sao cho tâm block đáp đúng target_position.
        """
        best_angle = 90.0
        best_error = float("inf")

        for candidate_angle in (
            -90.0,
            90.0
        ):
            rotation_delta = Quat()
            rotation_delta.setFromAxisAngle(
                candidate_angle,
                self.axis
            )

            candidate_position = (
                self.pivot_position
                + rotation_delta.xform(
                    self.start_offset
                )
            )

            difference = (
                candidate_position
                - self.target_position
            )

            error = (
                difference.x * difference.x
                + difference.y * difference.y
                + difference.z * difference.z
            )

            if error < best_error:
                best_error = error
                best_angle = candidate_angle

        if best_error > 1e-5:
            raise RuntimeError(
                "Roll geometry does not match the target state. "
                f"Best squared error: {best_error:.8f}"
            )

        return best_angle


class BlockView:
    """
    Hiển thị và phát animation cho block Bloxorz.

    Phiên bản này dùng chuyển động rigid-body thực:
    - Kích thước model khớp kích thước lưới 1 x 2 x 1.
    - Pivot là cạnh đang tiếp xúc với mặt board.
    - Tâm và hướng block dùng chung một quaternion.
    - Không tween position riêng, không nâng block giả.
    """

    BOARD_TOP_Y = 0.10

    # Để lăn không trượt, kích thước render phải khớp grid.
    # Nếu thu nhỏ còn 0.82 x 1.82, cạnh model không chạm pivot và
    # chuyển động tất yếu trông giống đang bay quanh một điểm vô hình.
    BLOCK_WIDTH = 1.0
    BLOCK_LENGTH = 2.0
    CUBE_SIZE = 1.0

    MOVE_DURATION = 0.17

    # Goal animation:
    # block đứng yên một nhịp ngắn rồi chìm thẳng xuống tâm hố.
    GOAL_PAUSE_DURATION = 0.10
    GOAL_DROP_DURATION = 0.58
    GOAL_DROP_DISTANCE = 2.40

    NORMAL_BLOCK_COLOR = color.rgb32(
        115,
        68,
        45
    )

    CUBE_1_COLOR = color.rgb32(
        75,
        145,
        220
    )

    CUBE_2_COLOR = color.rgb32(
        155,
        95,
        210
    )

    ACTIVE_CUBE_COLOR = color.rgb32(
        255,
        205,
        65
    )

    ACTIVE_MARKER_COLOR = color.rgb32(
        255,
        245,
        160
    )


    def __init__(self) -> None:
        self.root = Entity(
            name="BlockRoot"
        )

        self.normal_block = Entity(
            parent=self.root,
            name="NormalBlock",
            model="cube",
            texture="white_cube",
            scale=(
                self.BLOCK_WIDTH,
                self.BLOCK_LENGTH,
                self.BLOCK_WIDTH
            ),
            color=self.NORMAL_BLOCK_COLOR,
            shader=lit_with_shadows_shader,
            collider=None,
            enabled=False
        )

        self.cube_1 = Entity(
            parent=self.root,
            name="SplitCube1",
            model="cube",
            texture="white_cube",
            scale=self.CUBE_SIZE,
            color=self.CUBE_1_COLOR,
            shader=lit_with_shadows_shader,
            collider=None,
            enabled=False
        )

        self.cube_2 = Entity(
            parent=self.root,
            name="SplitCube2",
            model="cube",
            texture="white_cube",
            scale=self.CUBE_SIZE,
            color=self.CUBE_2_COLOR,
            shader=lit_with_shadows_shader,
            collider=None,
            enabled=False
        )

        self.cube_1_marker = Entity(
            parent=self.cube_1,
            name="Cube1ActiveMarker",
            model="sphere",
            position=(
                0,
                0.57,
                0
            ),
            scale=0.16,
            color=self.ACTIVE_MARKER_COLOR,
            enabled=False
        )

        self.cube_2_marker = Entity(
            parent=self.cube_2,
            name="Cube2ActiveMarker",
            model="sphere",
            position=(
                0,
                0.57,
                0
            ),
            scale=0.16,
            color=self.ACTIVE_MARKER_COLOR,
            enabled=False
        )


    def update(
        self,
        state: State
    ) -> None:
        mode_name = self._get_enum_name(
            state.mode
        )

        if mode_name == "NORMAL":
            self._show_normal_mode(
                state
            )
            return

        if mode_name == "SPLIT":
            self._show_split_mode(
                state
            )
            return

        raise ValueError(
            f"Unsupported block mode for GUI: {state.mode}"
        )


    def play_move(
        self,
        previous_state: State,
        resulting_state: State,
        action: str,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        normalized_action = (
            action.strip().upper()
        )

        if normalized_action in {
            SWITCH_CUBE,
            "SPACE"
        }:
            self.update(
                resulting_state
            )
            self._call_if_present(
                on_complete
            )
            return

        if normalized_action not in {
            UP,
            DOWN,
            LEFT,
            RIGHT
        }:
            self.update(
                resulting_state
            )
            self._call_if_present(
                on_complete
            )
            return

        previous_mode = self._get_enum_name(
            previous_state.mode
        )

        if previous_mode == "NORMAL":
            self._play_normal_roll(
                previous_state=previous_state,
                resulting_state=resulting_state,
                action=normalized_action,
                on_complete=on_complete
            )
            return

        if previous_mode == "SPLIT":
            self._play_split_cube_roll(
                previous_state=previous_state,
                resulting_state=resulting_state,
                action=normalized_action,
                on_complete=on_complete
            )
            return

        self.update(
            resulting_state
        )
        self._call_if_present(
            on_complete
        )


    def _show_normal_mode(
        self,
        state: State
    ) -> None:
        self.normal_block.enabled = True
        self.cube_1.enabled = False
        self.cube_2.enabled = False

        self.cube_1_marker.enabled = False
        self.cube_2_marker.enabled = False

        position, rotation = (
            self._normal_transform(
                state
            )
        )

        self.normal_block.parent = self.root
        self.normal_block.position = position
        self.normal_block.rotation = rotation
        self.normal_block.scale = (
            self.BLOCK_WIDTH,
            self.BLOCK_LENGTH,
            self.BLOCK_WIDTH
        )


    def _show_split_mode(
        self,
        state: State
    ) -> None:
        if (
            state.cube1 is None
            or state.cube2 is None
        ):
            raise ValueError(
                "Split mode requires cube1 and cube2."
            )

        self.normal_block.enabled = False
        self.cube_1.enabled = True
        self.cube_2.enabled = True

        cube_1_row, cube_1_col = (
            state.cube1
        )
        cube_2_row, cube_2_col = (
            state.cube2
        )

        self.cube_1.parent = self.root
        self.cube_1.position = (
            self._cube_world_position(
                cube_1_row,
                cube_1_col
            )
        )
        self.cube_1.rotation = (
            0,
            0,
            0
        )
        self.cube_1.scale = (
            self.CUBE_SIZE
        )

        self.cube_2.parent = self.root
        self.cube_2.position = (
            self._cube_world_position(
                cube_2_row,
                cube_2_col
            )
        )
        self.cube_2.rotation = (
            0,
            0,
            0
        )
        self.cube_2.scale = (
            self.CUBE_SIZE
        )

        active_cube = (
            state.active_cube
        )

        if active_cube not in {
            1,
            2
        }:
            raise ValueError(
                f"active_cube must be 1 or 2, got {active_cube}."
            )

        cube_1_is_active = (
            active_cube == 1
        )
        cube_2_is_active = (
            active_cube == 2
        )

        self.cube_1.color = (
            self.ACTIVE_CUBE_COLOR
            if cube_1_is_active
            else self.CUBE_1_COLOR
        )

        self.cube_2.color = (
            self.ACTIVE_CUBE_COLOR
            if cube_2_is_active
            else self.CUBE_2_COLOR
        )

        self.cube_1_marker.enabled = (
            cube_1_is_active
        )
        self.cube_2_marker.enabled = (
            cube_2_is_active
        )


    def _play_normal_roll(
        self,
        previous_state: State,
        resulting_state: State,
        action: str,
        on_complete: Callable[[], None] | None
    ) -> None:
        # Mỗi nước đi bắt đầu từ canonical orientation của State.
        #
        # Không giữ quaternion tích lũy giữa các bước vì quaternion đó
        # còn chứa các vòng quay đối xứng 180/360 độ. Khi đổi hướng,
        # các vòng quay dư có thể làm trục dài của block hiển thị sai
        # dù Game state vẫn đúng.
        #
        # Việc snap về canonical orientation không nhìn thấy được vì
        # các orientation tương đương có cùng hình dạng và texture.
        self.update(
            previous_state
        )

        start_position = Vec3(
            self.normal_block.position
        )

        target_position = Vec3(
            self._normal_transform(
                resulting_state
            )[0]
        )

        pivot_position = Vec3(
            self._normal_roll_pivot(
                state=previous_state,
                action=action
            )
        )

        axis = (
            Vec3(1, 0, 0)
            if action in {UP, DOWN}
            else Vec3(0, 0, 1)
        )

        def finish_animation() -> None:
            # Driver đã hoàn thành đúng một lần lăn 90 độ quanh cạnh.
            # Sau đó snap về canonical transform tương ứng với State.
            #
            # Đây không phải một animation bổ sung. Với cube texture
            # đồng nhất, các rotation chênh nhau 180/360 độ là cùng
            # một hình dạng nên người chơi không thấy block quay thêm.
            self.update(
                resulting_state
            )

            self._call_if_present(
                on_complete
            )

        _PhysicalRollDriver(
            rig=self.normal_block,
            start_position=start_position,
            target_position=target_position,
            pivot_position=pivot_position,
            axis=axis,
            duration=self.MOVE_DURATION,
            on_complete=finish_animation
        )


    def _play_split_cube_roll(
        self,
        previous_state: State,
        resulting_state: State,
        action: str,
        on_complete: Callable[[], None] | None
    ) -> None:
        if (
            previous_state.cube1 is None
            or previous_state.cube2 is None
        ):
            raise ValueError(
                "Split move requires cube1 and cube2."
            )

        self.update(
            previous_state
        )

        if previous_state.active_cube == 1:
            moving_cube = self.cube_1
            start_row, start_col = (
                previous_state.cube1
            )

        elif previous_state.active_cube == 2:
            moving_cube = self.cube_2
            start_row, start_col = (
                previous_state.cube2
            )

        else:
            raise ValueError(
                "active_cube must be 1 or 2."
            )

        row_delta, col_delta = {
            UP: (-1, 0),
            DOWN: (1, 0),
            LEFT: (0, -1),
            RIGHT: (0, 1)
        }[action]

        target_row = (
            start_row + row_delta
        )
        target_col = (
            start_col + col_delta
        )

        start_position = Vec3(
            moving_cube.position
        )

        target_position = Vec3(
            self._cube_world_position(
                target_row,
                target_col
            )
        )

        pivot_position = Vec3(
            self._cube_roll_pivot(
                cube_position=start_position,
                action=action
            )
        )

        axis = (
            Vec3(1, 0, 0)
            if action in {UP, DOWN}
            else Vec3(0, 0, 1)
        )

        def finish_animation() -> None:
            self.update(
                resulting_state
            )
            self._call_if_present(
                on_complete
            )

        _PhysicalRollDriver(
            rig=moving_cube,
            start_position=start_position,
            target_position=target_position,
            pivot_position=pivot_position,
            axis=axis,
            duration=self.MOVE_DURATION,
            on_complete=finish_animation
        )


    def _normal_roll_pivot(
        self,
        state: State,
        action: str
    ) -> tuple[float, float, float]:
        """
        Trung điểm cạnh đáy theo hướng di chuyển.
        """
        center, _ = (
            self._normal_transform(
                state
            )
        )

        center_x, _, center_z = (
            center
        )

        orientation_name = self._get_enum_name(
            state.orientation
        )

        if orientation_name == "STANDING":
            half_x = (
                self.BLOCK_WIDTH / 2
            )
            half_z = (
                self.BLOCK_WIDTH / 2
            )

        elif orientation_name == "HORIZONTAL":
            half_x = (
                self.BLOCK_LENGTH / 2
            )
            half_z = (
                self.BLOCK_WIDTH / 2
            )

        elif orientation_name == "VERTICAL":
            half_x = (
                self.BLOCK_WIDTH / 2
            )
            half_z = (
                self.BLOCK_LENGTH / 2
            )

        else:
            raise ValueError(
                f"Unsupported orientation: {state.orientation}"
            )

        if action == LEFT:
            return (
                center_x - half_x,
                self.BOARD_TOP_Y,
                center_z
            )

        if action == RIGHT:
            return (
                center_x + half_x,
                self.BOARD_TOP_Y,
                center_z
            )

        if action == UP:
            return (
                center_x,
                self.BOARD_TOP_Y,
                center_z + half_z
            )

        if action == DOWN:
            return (
                center_x,
                self.BOARD_TOP_Y,
                center_z - half_z
            )

        raise ValueError(
            f"Unsupported action: {action}"
        )


    def _cube_roll_pivot(
        self,
        cube_position: Vec3,
        action: str
    ) -> tuple[float, float, float]:
        half_size = (
            self.CUBE_SIZE / 2
        )

        if action == LEFT:
            return (
                cube_position.x - half_size,
                self.BOARD_TOP_Y,
                cube_position.z
            )

        if action == RIGHT:
            return (
                cube_position.x + half_size,
                self.BOARD_TOP_Y,
                cube_position.z
            )

        if action == UP:
            return (
                cube_position.x,
                self.BOARD_TOP_Y,
                cube_position.z + half_size
            )

        if action == DOWN:
            return (
                cube_position.x,
                self.BOARD_TOP_Y,
                cube_position.z - half_size
            )

        raise ValueError(
            f"Unsupported action: {action}"
        )



    def play_goal_drop(
        self,
        goal_state: State,
        on_drop_started: Callable[[], None] | None = None,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        """
        Phát animation chiến thắng.

        Luồng:
        - Đặt block đứng thẳng chính xác tại Goal.
        - Giữ yên một nhịp ngắn.
        - Chìm thẳng xuống đúng tâm hố.
        - Không xoay và không dịch chuyển theo X/Z.
        - Ẩn block sau khi đã xuống dưới board.
        """
        mode_name = self._get_enum_name(
            goal_state.mode
        )
        orientation_name = self._get_enum_name(
            goal_state.orientation
        )

        if mode_name != "NORMAL":
            raise ValueError(
                "Goal animation requires NORMAL mode."
            )

        if orientation_name != "STANDING":
            raise ValueError(
                "Goal animation requires STANDING orientation."
            )

        # Bảo đảm block nằm đúng tâm Goal và đứng thẳng.
        self.update(
            goal_state
        )

        goal_block = self.normal_block

        start_x = float(goal_block.x)
        start_z = float(goal_block.z)
        target_y = (
            float(goal_block.y)
            - self.GOAL_DROP_DISTANCE
        )

        def start_drop() -> None:
            self._call_if_present(
                on_drop_started
            )

            # Chỉ thay đổi Y. X/Z và rotation được giữ nguyên.
            goal_block.animate_y(
                target_y,
                duration=self.GOAL_DROP_DURATION,
                curve=curve.in_quad
            )

        def finish_drop() -> None:
            # Khóa lại X/Z để bảo đảm block chìm đúng tâm hố.
            goal_block.x = start_x
            goal_block.z = start_z
            goal_block.enabled = False

            self._call_if_present(
                on_complete
            )

        invoke(
            start_drop,
            delay=self.GOAL_PAUSE_DURATION
        )

        invoke(
            finish_drop,
            delay=(
                self.GOAL_PAUSE_DURATION
                + self.GOAL_DROP_DURATION
                + 0.03
            )
        )


    def play_fall(
        self,
        attempted_state: State,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        # Đưa block về transform đúng của attempted_state trước khi rơi.
        self.update(
            attempted_state
        )

        mode_name = self._get_enum_name(
            attempted_state.mode
        )

        if mode_name == "NORMAL":
            falling_entity = (
                self.normal_block
            )

        elif mode_name == "SPLIT":
            if attempted_state.active_cube == 1:
                falling_entity = (
                    self.cube_1
                )

            elif attempted_state.active_cube == 2:
                falling_entity = (
                    self.cube_2
                )

            else:
                raise ValueError(
                    "active_cube must be 1 or 2."
                )

        else:
            raise ValueError(
                f"Unsupported block mode: {attempted_state.mode}"
            )

        falling_entity.animate_y(
            falling_entity.y - 6,
            duration=0.75,
            curve=curve.in_quad
        )

        falling_entity.animate_rotation(
            (
                falling_entity.rotation_x + 120,
                falling_entity.rotation_y + 45,
                falling_entity.rotation_z + 90
            ),
            duration=0.75,
            curve=curve.in_quad
        )

        if on_complete is not None:
            invoke(
                on_complete,
                delay=0.85
            )


    def _normal_transform(
        self,
        state: State
    ) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float]
    ]:
        orientation_name = self._get_enum_name(
            state.orientation
        )

        if orientation_name == "STANDING":
            position = (
                float(state.col),
                self.BOARD_TOP_Y
                + self.BLOCK_LENGTH / 2,
                float(-state.row)
            )

            rotation = (
                0.0,
                0.0,
                0.0
            )

        elif orientation_name == "HORIZONTAL":
            position = (
                float(state.col) + 0.5,
                self.BOARD_TOP_Y
                + self.BLOCK_WIDTH / 2,
                float(-state.row)
            )

            rotation = (
                0.0,
                0.0,
                90.0
            )

        elif orientation_name == "VERTICAL":
            position = (
                float(state.col),
                self.BOARD_TOP_Y
                + self.BLOCK_WIDTH / 2,
                -(float(state.row) + 0.5)
            )

            rotation = (
                90.0,
                0.0,
                0.0
            )

        else:
            raise ValueError(
                f"Unsupported orientation: {state.orientation}"
            )

        return (
            position,
            rotation
        )


    def _cube_world_position(
        self,
        row: int,
        col: int
    ) -> tuple[float, float, float]:
        return (
            float(col),
            self.BOARD_TOP_Y
            + self.CUBE_SIZE / 2,
            float(-row)
        )


    @staticmethod
    def _call_if_present(
        callback: Callable[[], None] | None
    ) -> None:
        if callback is not None:
            callback()


    @staticmethod
    def _get_enum_name(
        value
    ) -> str:
        enum_name = getattr(
            value,
            "name",
            None
        )

        if enum_name is not None:
            return str(
                enum_name
            ).upper()

        enum_value = getattr(
            value,
            "value",
            value
        )

        return str(
            enum_value
        ).split(".")[-1].upper()


    def set_visible(
        self,
        is_visible: bool
    ) -> None:
        self.root.enabled = (
            is_visible
        )