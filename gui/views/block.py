from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ursina import Entity, color, curve, invoke
from ursina.shaders import lit_with_shadows_shader

if TYPE_CHECKING:
    from core.state import State


class BlockView:
    """
    Hiển thị block của game Bloxorz bằng Ursina.

    BlockView chỉ chịu trách nhiệm hiển thị:
    - Block đứng.
    - Block nằm ngang.
    - Block nằm dọc.
    - Hai cube khi block ở split mode.
    - Cube đang được điều khiển.

    BlockView không:
    - Xử lý bàn phím.
    - Thực hiện game.move().
    - Kiểm tra thắng/thua.
    - Thay đổi State.
    """

    # Mặt trên của tile nằm tại:
    # tile center y = 0
    # tile height   = 0.20
    # nên mặt trên của tile là 0.20 / 2 = 0.10.
    BOARD_TOP_Y = 0.10

    # Block nhỏ hơn tile một chút để giữa block và tile
    # có khoảng trống, giúp hình ảnh dễ nhìn hơn.
    BLOCK_WIDTH = 0.82

    # Khi block nằm, chiều dài gần bằng hai tile.
    # Hai tâm tile cách nhau 1 đơn vị.
    BLOCK_LENGTH = 1.82

    # Kích thước của mỗi cube sau khi split.
    CUBE_SIZE = 0.82

    # ---------------------------------------------------------
    # Màu sắc
    # ---------------------------------------------------------
    # color.rgb32(red, green, blue)
    # Mỗi giá trị nằm trong khoảng 0 đến 255.
    # Bạn không cần ghi nhớ mã màu, chỉ cần sửa các số ở đây
    # nếu muốn đổi giao diện sau này.

    # Màu block bình thường: nâu cam.
    NORMAL_BLOCK_COLOR = color.rgb32(115, 68, 45) 

    # Màu cube 1 khi không được điều khiển: xanh dương.
    CUBE_1_COLOR = color.rgb32(75, 145, 220)

    # Màu cube 2 khi không được điều khiển: tím.
    CUBE_2_COLOR = color.rgb32(155, 95, 210)

    # Cube đang được điều khiển sẽ chuyển sang màu vàng.
    ACTIVE_CUBE_COLOR = color.rgb32(255, 205, 65)

    # Màu của dấu hiệu nằm trên cube đang active.
    ACTIVE_MARKER_COLOR = color.rgb32(255, 245, 160)

    def __init__(self):
        """
        Tạo các Entity cần thiết.

        Ta tạo sẵn:
        - Một Entity cho normal block.
        - Một Entity cho cube 1.
        - Một Entity cho cube 2.

        Sau đó update() sẽ quyết định Entity nào được hiển thị.
        """

        # Root chứa toàn bộ các Entity của block.
        # Sau này menu có thể ẩn toàn bộ block bằng:
        # self.block_view.root.enabled = False
        self.root = Entity(name="BlockRoot")

        # Block 1 × 1 × 2 ở normal mode.
        self.normal_block = Entity(
            parent=self.root,
            name="NormalBlock",
            model="cube",
            texture="white_cube",
            color=self.NORMAL_BLOCK_COLOR,
            shader=lit_with_shadows_shader,
            collider=None,
            enabled=False
        )

        # Cube thứ nhất trong split mode.
        self.cube_1 = Entity(
            parent=self.root,
            name="SplitCube1",
            model="cube",
            texture="white_cube",
            color=self.CUBE_1_COLOR,
            shader=lit_with_shadows_shader,
            collider=None,
            enabled=False
        )

        # Cube thứ hai trong split mode.
        self.cube_2 = Entity(
            parent=self.root,
            name="SplitCube2",
            model="cube",
            texture="white_cube",
            color=self.CUBE_2_COLOR,
            shader=lit_with_shadows_shader,
            collider=None,
            enabled=False
        )

        # Dấu hiệu nhỏ nằm trên cube 1 khi cube 1 đang được điều khiển.
        self.cube_1_marker = Entity(
            parent=self.cube_1,
            name="Cube1ActiveMarker",
            model="sphere",
            position=(0, 0.75, 0),
            scale=0.18,
            color=self.ACTIVE_MARKER_COLOR,
            enabled=False
        )

        # Dấu hiệu nhỏ nằm trên cube 2 khi cube 2 đang được điều khiển.
        self.cube_2_marker = Entity(
            parent=self.cube_2,
            name="Cube2ActiveMarker",
            model="sphere",
            position=(0, 0.75, 0),
            scale=0.18,
            color=self.ACTIVE_MARKER_COLOR,
            enabled=False
        )


    def update(self, state: State) -> None:
        """
        Cập nhật hình ảnh block theo State hiện tại.

        Có hai mode:

        NORMAL:
            Hiển thị block 1 × 1 × 2.

        SPLIT:
            Ẩn normal block và hiển thị hai cube 1 × 1 × 1.
        """
        mode_name = self._get_enum_name(state.mode)

        if mode_name == "NORMAL":
            self._show_normal_mode(state)

        elif mode_name == "SPLIT":
            self._show_split_mode(state)

        else:
            raise ValueError(
                f"Unsupported block mode for GUI: {state.mode}"
            )


    def _show_normal_mode(self, state: State) -> None:
        """
        Hiển thị block trong normal mode.
        Tùy orientation, block sẽ có position và scale khác nhau.
        """
        self.normal_block.enabled = True

        self.cube_1.enabled = False
        self.cube_2.enabled = False
        self.cube_1_marker.enabled = False
        self.cube_2_marker.enabled = False

        orientation_name = self._get_enum_name(
            state.orientation
        )

        if orientation_name == "STANDING":
            self._update_standing_block(
                row=state.row,
                col=state.col
            )

        elif orientation_name == "HORIZONTAL":
            self._update_horizontal_block(
                row=state.row,
                col=state.col
            )

        elif orientation_name == "VERTICAL":
            self._update_vertical_block(
                row=state.row,
                col=state.col
            )

        else:
            raise ValueError(
                f"Unsupported orientation for GUI: "
                f"{state.orientation}"
            )


    def _update_standing_block(
        self,
        row: int,
        col: int
    ) -> None:
        """
        Block đang đứng.

        Nó chiếm một tile nhưng cao hai đơn vị.

        Scale:
            x = chiều rộng một tile
            y = chiều cao hai cube
            z = chiều rộng một tile
        """
        block_height = self.BLOCK_LENGTH

        self.normal_block.position = (
            float(col),
            self.BOARD_TOP_Y + block_height / 2,
            float(-row)
        )

        self.normal_block.scale = (
            self.BLOCK_WIDTH,
            block_height,
            self.BLOCK_WIDTH
        )

        # Reset rotation để tránh giữ rotation cũ nếu sau này
        # có thêm animation.
        self.normal_block.rotation = (0, 0, 0)


    def _update_horizontal_block(
        self,
        row: int,
        col: int
    ) -> None:
        """
        Block nằm ngang theo hai cột:

            (row, col)
            (row, col + 1)

        Tâm block nằm giữa hai tile nên x = col + 0.5.
        """
        block_height = self.BLOCK_WIDTH

        self.normal_block.position = (
            float(col) + 0.5,
            self.BOARD_TOP_Y + block_height / 2,
            float(-row)
        )

        self.normal_block.scale = (
            self.BLOCK_LENGTH,
            block_height,
            self.BLOCK_WIDTH
        )

        self.normal_block.rotation = (0, 0, 0)


    def _update_vertical_block(
        self,
        row: int,
        col: int
    ) -> None:
        """
        Block nằm dọc theo hai hàng:

            (row, col)
            (row + 1, col)

        Vì z = -row nên tâm theo trục z là:

            z = -(row + 0.5)
        """
        block_height = self.BLOCK_WIDTH

        self.normal_block.position = (
            float(col),
            self.BOARD_TOP_Y + block_height / 2,
            -(float(row) + 0.5)
        )

        self.normal_block.scale = (
            self.BLOCK_WIDTH,
            block_height,
            self.BLOCK_LENGTH
        )

        self.normal_block.rotation = (0, 0, 0)


    def _show_split_mode(self, state: State) -> None:
        """
        State cần có:
            state.cube1 = (row, col)
            state.cube2 = (row, col)
            state.active_cube = 1 hoặc 2

        Quy ước:
            1 -> cube 1 đang được điều khiển
            2 -> cube 2 đang được điều khiển
        """
        if state.cube1 is None or state.cube2 is None:
            raise ValueError(
                "Split mode requires both cube1 and cube2 positions."
            )

        self.normal_block.enabled = False

        self.cube_1.enabled = True
        self.cube_2.enabled = True

        cube_1_row, cube_1_col = state.cube1
        cube_2_row, cube_2_col = state.cube2

        # Đặt cube 1 vào đúng tile và reset hình ảnh cũ.
        self.cube_1.position = self._cube_world_position(
            cube_1_row,
            cube_1_col
        )

        self.cube_1.scale = (
            self.CUBE_SIZE,
            self.CUBE_SIZE,
            self.CUBE_SIZE
        )

        # Xóa rotation còn sót lại từ animation rơi trước đó.
        self.cube_1.rotation = (0, 0, 0)


        # Đặt cube 2 vào đúng tile và reset hình ảnh cũ.
        self.cube_2.position = self._cube_world_position(
            cube_2_row,
            cube_2_col
        )

        self.cube_2.scale = (
            self.CUBE_SIZE,
            self.CUBE_SIZE,
            self.CUBE_SIZE
        )

        # Xóa rotation còn sót lại từ animation rơi trước đó.
        self.cube_2.rotation = (0, 0, 0)

        active_cube = state.active_cube

        if active_cube not in {1, 2}:
            raise ValueError(
                f"active_cube must be 1 or 2, got: {active_cube}"
            )

        cube_1_is_active = active_cube == 1
        cube_2_is_active = active_cube == 2

        # Cube active chuyển sang màu vàng.
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

        # Chỉ cube active mới có dấu tròn phía trên.
        self.cube_1_marker.enabled = cube_1_is_active
        self.cube_2_marker.enabled = cube_2_is_active


    def _cube_world_position(
        self,
        row: int,
        col: int
    ) -> tuple[float, float, float]:
        """
        Chuyển vị trí một cube từ grid sang Ursina world position.

        Cube cao CUBE_SIZE nên tâm của nó nằm tại:

            BOARD_TOP_Y + CUBE_SIZE / 2
        """
        return (
            float(col),
            self.BOARD_TOP_Y + self.CUBE_SIZE / 2,
            float(-row)
        )


    def play_fall(
        self,
        attempted_state: State,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        """
        Đặt block vào vị trí nước đi thất bại rồi làm nó rơi xuống.

        attempted_state:
            State mà block/cube đã cố di chuyển đến.

        on_complete:
            Callback được gọi sau khi animation kết thúc.
        """
        self.update(attempted_state)

        mode_name = self._get_enum_name(
            attempted_state.mode
        )

        if mode_name == "NORMAL":
            falling_entity = self.normal_block

        elif mode_name == "SPLIT":
            if attempted_state.active_cube == 1:
                falling_entity = self.cube_1
            elif attempted_state.active_cube == 2:
                falling_entity = self.cube_2
            else:
                raise ValueError(
                    "active_cube must be 1 or 2"
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


    @staticmethod
    def _get_enum_name(value) -> str:
        """
        Lấy tên từ một Enum theo cách an toàn.

        Ví dụ:

            BlockMode.NORMAL       -> "NORMAL"
            Orientation.STANDING   -> "STANDING"

        Hàm này giúp BlockView không cần biết enum được định nghĩa
        chính xác ở file nào.
        """
        enum_name = getattr(value, "name", None)

        if enum_name is not None:
            return str(enum_name).upper()

        enum_value = getattr(value, "value", value)

        return str(enum_value).split(".")[-1].upper()


    def set_visible(self, is_visible: bool) -> None:
        """
        Ẩn hoặc hiện toàn bộ block.

        Dùng cho menu hoặc chuyển scene.
        """
        self.root.enabled = is_visible