from ursina import (
    Entity,
    color,
    curve, 
    invoke,
    destroy,
)
from core.state import (
    BlockMode,
    Orientation,
)


class BlockView:
    def __init__(self, tile_size: float = 1.0):
        self.tile_size = tile_size

        self.root = Entity(name="BlockView")

        self.normal_block = None
        self.cube1 = None
        self.cube2 = None

    def update(self, state):
        if state.mode == BlockMode.NORMAL:
            self.show_normal_block(state)
        elif state.mode == BlockMode.SPLIT:
            self.show_split_blocks(state)

    def show_normal_block(self, state):
        self.hide_split_blocks()

        if self.normal_block is None:
            self.normal_block = Entity(
                parent=self.root,
                model="cube",
                texture="white_cube",
                color=color.orange,
                collider="box",
                name="NormalBlock",
            )

        self.normal_block.enabled = True
        self.normal_block.position = self.get_normal_position(state)
        self.normal_block.scale = self.get_normal_scale(state)

    def show_split_blocks(self, state):
        self.hide_normal_block()

        if self.cube1 is None:
            self.cube1 = self.create_cube("Cube1")

        if self.cube2 is None:
            self.cube2 = self.create_cube("Cube2")

        cube1_row, cube1_col = state.cube1
        cube2_row, cube2_col = state.cube2

        self.cube1.enabled = True
        self.cube2.enabled = True

        self.cube1.position = self.get_cube_position(cube1_row, cube1_col)
        self.cube2.position = self.get_cube_position(cube2_row, cube2_col)

        self.cube1.color = color.azure if state.active_cube == 1 else color.dark_gray
        self.cube2.color = color.azure if state.active_cube == 2 else color.dark_gray

    def create_cube(self, name: str) -> Entity:
        return Entity(
            parent=self.root,
            model="cube",
            texture="white_cube",
            scale=(0.85, 0.85, 0.85),
            color=color.azure,
            collider="box",
            name=name,
        )

    def get_normal_position(self, state):
        ori = str(state.orientation).upper()
        # Lấy tọa độ lưới
        x = state.col
        z = -state.row
        
        # Căn chỉnh tâm:
        # Nếu đang đứng (Standing), nằm trên 1 ô -> Tâm x,z khớp với x,z lưới.
        if "STAND" in ori or "UP" in ori:
            return (x, 0.85, z)
            
        # Nếu nằm ngang (Horizontal), nó chiếm 2 ô. Tâm của nó nằm giữa 2 ô đó.
        # Ở đây con thêm -0.5 để đẩy tâm về đúng giữa ô gạch phía trước.
        if "HORI" in ori or "ROW" in ori or "X" in ori:
            return (x + 0.5, 0.425, z)
            
        # Nếu nằm dọc (Vertical), tương tự căn chỉnh trên trục Z.
        if "VERT" in ori or "COL" in ori or "Y" in ori or "Z" in ori:
            return (x, 0.425, z - 0.5)
            
        return (x, 0.85, z)

    def get_normal_scale(self, state):
        ori = str(state.orientation).upper()
        
        # Đứng (cao)
        if "STAND" in ori or "UP" in ori:
            return 0.85, 1.7, 0.85
        # Nằm ngang (rộng)
        if "HORI" in ori or "ROW" in ori or "X" in ori:
            return 1.7, 0.85, 0.85
        # Nằm dọc (dài)
        if "VERT" in ori or "COL" in ori or "Y" in ori or "Z" in ori:
            return 0.85, 0.85, 1.7
            
        return 0.85, 1.7, 0.85
    def show_normal_block(self, state):
        self.hide_split_blocks()

        if self.normal_block is None:
            self.normal_block = Entity(
                parent=self.root,
                model="cube",
                texture="white_cube",
                color=color.orange,
                collider="box",
                name="NormalBlock",
            )

        self.normal_block.enabled = True
        self.normal_block.position = self.get_normal_position(state)
        # TRẢ LẠI SCALE THAY ĐỔI LINH HOẠT VÀ ÉP GÓC XOAY VỀ 0
        self.normal_block.scale = self.get_normal_scale(state)
        self.normal_block.rotation = (0, 0, 0)

    def get_cube_position(self, row: int, col: int):
        x = col * self.tile_size
        y = 0.5
        z = -row * self.tile_size
        return x, y, z

    def hide_normal_block(self):
        if self.normal_block is not None:
            self.normal_block.enabled = False

    def hide_split_blocks(self):
        if self.cube1 is not None:
            self.cube1.enabled = False

        if self.cube2 is not None:
            self.cube2.enabled = False

    def destroy(self):
        self.root.disable()

    def animate_to_state(self, old_state, new_state, duration=0.25):
        if new_state.mode == BlockMode.NORMAL:
            # 1. Lấy vị trí và kích thước chuẩn
            new_pos = self.get_normal_position(new_state)
            new_scale = self.get_normal_scale(new_state)
            
            # 2. Reset góc xoay về 0 (để không bị lệch trục lật ngã nữa)
            self.normal_block.rotation = (0, 0, 0)
            
            # 3. Trượt vị trí mượt mà
            self.normal_block.animate('x', new_pos[0], duration=duration, curve=curve.linear)
            self.normal_block.animate('z', new_pos[2], duration=duration, curve=curve.linear)
            
            # 4. Phình ngang / Co lại (Squash & Stretch)
            self.normal_block.animate_scale(new_scale, duration=duration, curve=curve.in_out_quad)

            # 5. Tạo độ nảy nhẹ nhàng
            mid_y = max(self.normal_block.y, new_pos[1]) + 0.3
            self.normal_block.animate('y', mid_y, duration=duration/2, curve=curve.out_sine)
            invoke(lambda: self.normal_block.animate('y', new_pos[1], duration=duration/2, curve=curve.in_sine), delay=duration/2)
            
        elif new_state.mode == BlockMode.SPLIT:
            self.update(new_state)

    def clear_block(self):
        if self.normal_block:
            destroy(self.normal_block)
            self.normal_block = None

    def get_initial_rotation(self, state):
        if state.orientation == Orientation.STANDING:
            return (0, 0, 0)
        elif state.orientation == Orientation.HORIZONTAL:
            return (0, 0, 90)
        elif state.orientation == Orientation.VERTICAL:
            return (90, 0, 0)