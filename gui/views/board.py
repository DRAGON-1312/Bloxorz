from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ursina import Entity, color, curve, destroy, Cylinder, invoke
from ursina.shaders import lit_with_shadows_shader

from core.tiles import TileType

if TYPE_CHECKING:
    from core.board import Board
    from core.state import State


class BoardView:
    """
    Hiển thị Board của game bằng Ursina.

    Trách nhiệm:
    - Tạo mô hình 3D cho các tile không phải VOID.
    - Phân biệt từng loại tile bằng màu sắc và hình dạng.
    - Cập nhật trạng thái mở/đóng của bridge.
    - Tải lại toàn bộ board khi chuyển level.

    BoardView chỉ hiển thị dữ liệu.
    Nó không thay đổi game state và không xử lý input.
    """

    # Kích thước cơ bản của một ô trên board.
    TILE_SIZE = 1.0

    # Độ dày của tile.
    TILE_HEIGHT = 0.20

    # Khoảng cách nhỏ giữa các tile để nhìn rõ ranh giới.
    TILE_GAP = 0.04

    def __init__(self, board: Board):
        self.board = board

        # Root chứa toàn bộ Entity thuộc board.
        # Khi chuyển level, chỉ cần destroy root cũ rồi tạo root mới.
        self.root = Entity(name="BoardRoot")

        # Lưu Entity chính của từng ô:
        # (row, col) -> Entity
        self.tile_entities: dict[tuple[int, int], Entity] = {}

        # Ánh xạ vị trí bridge sang bridge id:
        # (row, col) -> bridge_id
        self.bridge_id_by_position: dict[tuple[int, int], int] = {}

        # Lưu Entity của bridge theo bridge id.
        # bridge_id -> [Entity, Entity, ...]
        # Một bridge id có thể điều khiển nhiều vị trí.
        self.bridge_entities: dict[int, list[Entity]] = {}

        self._build_board()

    def load_board(self, board: Board) -> None:
        """
        Xóa board hiện tại và hiển thị board mới.

        Hàm này được gọi khi:
        - Chuyển level.
        - Load level từ menu.
        - New Game/Continue chuyển sang board khác.
        """
        self.board = board

        # Xóa toàn bộ Entity cũ khỏi Ursina scene.
        destroy(self.root)

        # Tạo root mới để chứa board mới.
        self.root = Entity(name="BoardRoot")

        self.tile_entities.clear()
        self.bridge_id_by_position.clear()
        self.bridge_entities.clear()

        self._build_board()

    def _build_board(self) -> None:
        """
        Tạo toàn bộ tile Entity từ self.board.grid.
        """
        self._build_bridge_position_map()

        for row in range(self.board.rows):
            for col in range(self.board.cols):
                tile_type = self.board.grid[row][col]

                # VOID là khoảng trống, không tạo Entity.
                if tile_type == TileType.VOID:
                    continue

                entity = self._create_tile_entity(
                    row=row,
                    col=col,
                    tile_type=tile_type
                )

                self.tile_entities[(row, col)] = entity

                if tile_type == TileType.BRIDGE:
                    bridge_id = self.bridge_id_by_position.get(
                        (row, col)
                    )

                    if bridge_id is None:
                        raise ValueError(
                            f"Bridge tile at ({row}, {col}) "
                            f"does not have bridge metadata."
                        )

                    self.bridge_entities.setdefault(
                        bridge_id,
                        []
                    ).append(entity)

        # Khi vừa load board, bridge được hiển thị theo initial_open.
        self._apply_initial_bridge_states()

    def _build_bridge_position_map(self) -> None:
        """
        Chuyển bridge metadata thành ánh xạ nhanh:

            (row, col) -> bridge_id

        Ví dụ metadata:

            {
                "id": 2,
                "positions": [[1, 4], [1, 5]]
            }

        sẽ tạo:

            (1, 4) -> 2
            (1, 5) -> 2
        """
        for bridge in self.board.bridges:
            bridge_id = bridge["id"]

            for position in bridge["positions"]:
                row, col = position

                self.bridge_id_by_position[(row, col)] = bridge_id

    def _create_tile_entity(
        self,
        row: int,
        col: int,
        tile_type: TileType
    ) -> Entity:
        """
        Tạo Entity cho một tile.

        Quy ước tọa độ Ursina:
        - x = col
        - y = chiều cao
        - z = -row

        Dùng -row cho trục z để grid hiển thị cùng chiều
        với dữ liệu hàng từ trên xuống dưới.
        """
        position = self.grid_to_world(row, col)

        tile = Entity(
            parent=self.root,
            name=f"{tile_type.name}_{row}_{col}",
            model="cube",
            position=position,
            scale=(
                self.TILE_SIZE - self.TILE_GAP,
                self.TILE_HEIGHT,
                self.TILE_SIZE - self.TILE_GAP
            ),
            color=self._get_tile_color(tile_type),
            texture="white_cube",
            collider="box",
            shader=lit_with_shadows_shader
        )

        # Thêm dấu hiệu trực quan cho các tile đặc biệt.
        if tile_type == TileType.GOAL:
            self._add_goal_marker(tile)

        elif tile_type == TileType.SOFT_SWITCH:
            self._add_soft_switch_marker(tile)

        elif tile_type == TileType.HEAVY_SWITCH:
            self._add_heavy_switch_marker(tile)

        elif tile_type == TileType.SPLIT_SWITCH:
            self._add_split_switch_marker(tile)

        return tile

    @staticmethod
    def _get_tile_color(tile_type: TileType):
        """
        Trả về màu đại diện cho từng loại tile.
        """
        tile_colors = {
            TileType.FLOOR: color.rgb32(145, 150, 155),
            TileType.GOAL: color.rgb32(45, 47, 52),
            TileType.FRAGILE: color.rgb32(190, 120, 55),
            TileType.BRIDGE: color.rgb32(65, 120, 155),
            TileType.SOFT_SWITCH: color.rgb32(70, 165, 95),
            TileType.HEAVY_SWITCH: color.rgb32(175, 65, 60),
            TileType.SPLIT_SWITCH: color.rgb32(125, 75, 170),
        }

        try:
            return tile_colors[tile_type]
        except KeyError as error:
            raise ValueError(
                f"Unsupported tile type for GUI: {tile_type}"
            ) from error

    def _add_goal_marker(self, tile: Entity) -> None:
        """
        Tạo một ô tối nằm trên goal để goal giống một cái hố.
        """
        Entity(
            parent=tile,
            name="GoalMarker",
            model="cube",
            position=(0, 0.56, 0),
            scale=(0.68, 0.08, 0.68),
            color=color.rgb32(15, 15, 20)
        )

    def _add_soft_switch_marker(self, tile: Entity) -> None:
        """
        Soft switch được biểu diễn bằng một đĩa tròn nhỏ.
        """
        Entity(
            parent=tile,
            name="SoftSwitchMarker",
            model=Cylinder(
                resolution=16,
                radius=0.5,
                height=1
            ),
            position=(0, 0.62, 0),
            scale=(0.55, 0.08, 0.55),
            color=color.rgb32(130, 255, 150),
            rotation=(0, 0, 0)
        )

    def _add_heavy_switch_marker(self, tile: Entity) -> None:
        """
        Heavy switch được biểu diễn bằng dấu X.
        """
        marker_1 = Entity(
            parent=tile,
            name="HeavySwitchMarker1",
            model="cube",
            position=(0, 0.62, 0),
            scale=(0.72, 0.08, 0.15),
            rotation_y=45,
            color=color.rgb32(255, 210, 210)
        )

        Entity(
            parent=tile,
            name="HeavySwitchMarker2",
            model="cube",
            position=(0, 0.62, 0),
            scale=(0.72, 0.08, 0.15),
            rotation_y=-45,
            color=marker_1.color
        )

    def _add_split_switch_marker(self, tile: Entity) -> None:
        """
        Split switch được biểu diễn bằng hai khối nhỏ tách rời,
        tượng trưng cho việc chia block thành hai cube.
        """
        Entity(
            parent=tile,
            name="SplitSwitchMarkerLeft",
            model="cube",
            position=(-0.20, 0.62, 0),
            scale=(0.22, 0.08, 0.55),
            color=color.rgb32(225, 195, 255)
        )

        Entity(
            parent=tile,
            name="SplitSwitchMarkerRight",
            model="cube",
            position=(0.20, 0.62, 0),
            scale=(0.22, 0.08, 0.55),
            color=color.rgb32(225, 195, 255)
        )

    def _apply_initial_bridge_states(self) -> None:
        """
        Hiển thị bridge theo trạng thái initial_open trong Board.
        """
        for bridge in self.board.bridges:
            bridge_id = bridge["id"]
            is_open = bridge.get("initial_open", False)

            self._set_bridge_visual(
                bridge_id=bridge_id,
                is_open=is_open
            )


    def play_fragile_break(
        self,
        row: int,
        col: int,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        """
        Phát animation khi block đứng trên fragile tile:

        1. Tile tối lại.
        2. Tile hạ xuống và thu nhỏ.
        3. Tile biến mất.
        4. Gọi callback để block bắt đầu rơi.
        """
        tile = self.tile_entities.get((row, col))

        if tile is None:
            raise ValueError(
                f"No tile entity exists at ({row}, {col})."
            )

        tile_type = self.board.grid[row][col]

        if tile_type != TileType.FRAGILE:
            raise ValueError(
                f"Tile at ({row}, {col}) is not fragile: "
                f"{tile_type}"
            )

        # Tile đang vỡ không còn đỡ block nữa.
        tile.collider = None

        # Giai đoạn 1: tile tối lại.
        tile.animate_color(
            color.rgb32(85, 55, 35),
            duration=0.12,
            curve=curve.linear
        )

        def collapse_tile() -> None:
            """
            Giai đoạn 2: tile hạ xuống và thu nhỏ.
            """
            tile.animate_y(
                -0.35,
                duration=0.22,
                curve=curve.in_quad
            )

            tile.animate_scale(
                (
                    0.18,
                    0.04,
                    0.18
                ),
                duration=0.22,
                curve=curve.in_quad
            )

        def finish_break() -> None:
            """
            Giai đoạn 3: ẩn tile rồi bắt đầu animation tiếp theo.
            """
            tile.enabled = False

            if on_complete is not None:
                on_complete()

        invoke(
            collapse_tile,
            delay=0.12
        )

        invoke(
            finish_break,
            delay=0.38
        )


    def reset_fragile_tiles(self) -> None:
        """
        Khôi phục các fragile tile sau khi restart level.

        Cần thiết vì play_fragile_break() đã:
        - Đổi màu.
        - Thu nhỏ.
        - Hạ tile xuống.
        - Ẩn tile.
        """
        for (row, col), tile in self.tile_entities.items():
            if self.board.grid[row][col] != TileType.FRAGILE:
                continue

            tile.enabled = True
            tile.position = self.grid_to_world(row, col)

            tile.scale = (
                self.TILE_SIZE - self.TILE_GAP,
                self.TILE_HEIGHT,
                self.TILE_SIZE - self.TILE_GAP
            )

            tile.color = self._get_tile_color(
                TileType.FRAGILE
            )

            tile.collider = "box"


    def update(self, state: State) -> None:
        """
        Cập nhật các phần động của board theo State hiện tại.

        Hiện tại phần động duy nhất của BoardView là bridge.

        State phải chứa:

            state.bridges = (True, False, ...)

        Trong đó:
        - True  -> bridge đang mở
        - False -> bridge đang đóng
        """
        for bridge_id, is_open in enumerate(state.bridges):
            self._set_bridge_visual(
                bridge_id=bridge_id,
                is_open=is_open
            )

    def _set_bridge_visual(
        self,
        bridge_id: int,
        is_open: bool
    ) -> None:
        """
        Thay đổi hình ảnh của tất cả tile thuộc một bridge id.

        Bridge mở:
        - Nằm ngang bằng với floor.
        - Màu rõ.
        - Có collider.

        Bridge đóng:
        - Hạ thấp xuống.
        - Mờ và tối hơn.
        - Không có collider.
        """
        entities = self.bridge_entities.get(bridge_id, [])

        for bridge_entity in entities:
            if is_open:
                bridge_entity.y = 0
                bridge_entity.scale_y = self.TILE_HEIGHT
                bridge_entity.color = color.rgb32(80, 145, 180)
                bridge_entity.collider = "box"

            else:
                # Không ẩn hoàn toàn để người chơi vẫn nhận biết
                # vị trí của bridge đang đóng.
                bridge_entity.y = -0.32
                bridge_entity.scale_y = 0.08
                bridge_entity.color = color.rgba32(
                    60,
                    70,
                    85,
                    110
                )
                bridge_entity.collider = None

    @staticmethod
    def grid_to_world(
        row: int,
        col: int
    ) -> tuple[float, float, float]:
        """
        Chuyển tọa độ grid sang tọa độ thế giới của Ursina.

        Grid:
            (row, col)

        Ursina:
            (x, y, z)

        Ta dùng:
            x = col
            y = 0
            z = -row
        """
        return float(col), 0.0, float(-row)