from ursina import (
    Entity,
    color,
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
            scale=(0.85, 0.85, 0.85),
            color=color.azure,
            collider="box",
            name=name,
        )

    def get_normal_position(self, state):
        row = state.row
        col = state.col

        if state.orientation == Orientation.STANDING:
            x = col * self.tile_size
            y = 0.65
            z = -row * self.tile_size
            return x, y, z

        if state.orientation == Orientation.HORIZONTAL:
            x = (col + 0.5) * self.tile_size
            y = 0.35
            z = -row * self.tile_size
            return x, y, z

        if state.orientation == Orientation.VERTICAL:
            x = col * self.tile_size
            y = 0.35
            z = -(row + 0.5) * self.tile_size
            return x, y, z

    def get_normal_scale(self, state):
        if state.orientation == Orientation.STANDING:
            return 0.85, 1.7, 0.85

        if state.orientation == Orientation.HORIZONTAL:
            return 1.7, 0.85, 0.85

        if state.orientation == Orientation.VERTICAL:
            return 0.85, 0.85, 1.7

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