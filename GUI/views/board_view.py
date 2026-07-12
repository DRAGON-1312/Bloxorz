from ursina import(
    Entity,
    color,
    destroy,
)
from core.tiles import TileType
from core.block import get_occupied_tiles

class BoardView:
    def __init__(self, board, tile_size: float = 1.0):
        self.board = board
        self.tile_size = tile_size

        self.tile_entities = {}
        self.bridge_entities = {}
        self.switch_entities = {}

        self.root = Entity(name="BoardView")

        self.build()

    def build(self):
        for row, line in enumerate(self.board.grid):
            for col, tile_type in enumerate(line):
                if tile_type == TileType.VOID:
                    continue

                entity = self.create_tile(row, col, tile_type)

                self.tile_entities[(row, col)] = entity

                if tile_type == TileType.BRIDGE:
                    bridge_id = self.board.get_bridge_id(row, col)
                    if bridge_id is not None:
                        self.bridge_entities.setdefault(bridge_id, []).append(entity)

                if tile_type in {
                    TileType.SOFT_SWITCH,
                    TileType.HEAVY_SWITCH,
                    TileType.SPLIT_SWITCH,
                }:
                    self.switch_entities[(row, col)] = entity

    def clear(self):
        for entity in self.tile_entities.values():
            destroy(entity)

        self.tile_entities.clear()
        self.bridge_entities.clear()
        self.switch_entities.clear()

    def load_board(self, board):
        self.clear()
        self.board = board
        self.build()

    def create_tile(self, row: int, col: int, tile_type: TileType) -> Entity:
        x, y, z = self.board_to_world(row, col)

        entity = Entity(
            parent=self.root,
            model="cube",
            position=(x, y, z),
            scale=(0.95, 0.15, 0.95),
            color=self.get_tile_color(tile_type),
            collider="box",
            name=f"Tile({row}, {col}) {tile_type.name}",
        )

        return entity

    def get_tile_color(self, tile_type):
        t_name = str(tile_type).split('.')[-1].upper()

        if t_name == "FLOOR":
            return color.gray        # Gạch thường màu xám
        if t_name == "GOAL":
            return color.red         # ĐÍCH ĐẾN màu đỏ rực cho dễ thấy
        if t_name == "FRAGILE":
            return color.orange      # Gạch mỏng màu cam
        if t_name == "BRIDGE":
            return color.cyan        # Cầu màu xanh lơ
        if t_name == "SOFT_SWITCH":
            return color.yellow      # Nút bấm nhẹ màu vàng
        if t_name == "HEAVY_SWITCH":
            return color.magenta     # Nút bấm nặng màu hồng/tím
        if t_name == "SPLIT_SWITCH":
            return color.green       # Nút tách khối màu xanh lá

        return color.white           # Mặc định
    def board_to_world(self, row: int, col: int) -> tuple[float, float, float]:
        x = col * self.tile_size
        y = 0
        z = -row * self.tile_size
        return x, y, z

    def update_bridges(self, bridge_states):
        for bridge_id, entities in self.bridge_entities.items():
            if bridge_id >= len(bridge_states):
                continue

            is_active = bridge_states[bridge_id]

            for entity in entities:
                entity.enabled = is_active
    
    def update_switches(self, state):
        occupied_positions = set(get_occupied_tiles(state))

        for position, entity in self.switch_entities.items():
            row, col = position
            tile_type = self.board.get_tile(row, col)

            if position in occupied_positions:
                entity.color = color.white
            else:
                entity.color = self.get_tile_color(tile_type)
                
    def update(self, state):
        self.update_bridges(state.bridges)
        self.update_switches(state)

    def destroy(self):
        self.clear()
        destroy(self.root)
