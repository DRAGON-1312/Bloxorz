from ursina import (
    Ursina,
    EditorCamera,
    window,
    camera,
    Vec3,
    Entity,
    time,
    lerp,
)
from core.level_loader import load_level
from core.game import Game
from core.state import BlockMode
from GUI.level_manager import LevelManager
from GUI.views.board_view import BoardView
from GUI.views.block_view import BlockView
from GUI.controller import GameController
from GUI.input_controller import InputController
from GUI.views.hud_view import HUD
from GUI.save_manager import SaveManager
from GUI.views.menu_view import MenuView


class BloxorzApp:
    def __init__(self):
        self.app = Ursina()

        self.save_manager = SaveManager()
        self.current_slot = None

        self.level_manager = LevelManager()
        self.board = self.level_manager.load_current_level()
        
        self.board_view = BoardView(self.board)
        self.block_view = BlockView()
        self.hud = HUD()
        
        self.game_controller = GameController(
            board=self.board,
            board_view=self.board_view,
            block_view=self.block_view,
            hud=self.hud,
        )
        
        self.hud.set_game_controller(self.game_controller)
        
        self.input_controller = InputController(
            game_controller=self.game_controller,
            level_manager=self.level_manager,
        )
        
        self.input_handler = Entity(name="InputHandler")
        self.input_handler.input = self.input #fixed add

        self.input_handler.update = self.update_camera_follow #camera move

        self.setup_window()
        self.setup_camera()

        # --- LOGIC MENU Ở ĐÂY ---
        # 1. Ẩn toàn bộ bàn cờ và HUD đi khi mới mở app
        self.board_view.root.enabled = False
        self.block_view.root.enabled = False
        self.hud_set_visible(False) # Viết thêm hàm nhỏ này ở dưới nhé
        
        # 2. Khởi tạo và bật Menu lên
        self.menu_view = MenuView(on_start_callback=self.start_game_from_menu)

    def setup_window(self):
        window.title = "Bloxorz - A Project of an Introduction to AI Course"
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = False
        window.fps_counter.enabled = True

    # def setup_camera(self):
    #     camera.position = (10, 5, -10)
    #     camera.rotation_x = 30
    #     camera.rotation_y = -60

    #     # Tạm thời dùng EditorCamera để xoay/zoom bằng chuột khi debug.
    #     EditorCamera()
    
    # Hàm mồi để ẩn/hiện text của HUD
    def hud_set_visible(self, is_visible):
        self.hud.level_text.enabled = is_visible
        self.hud.move_text.enabled = is_visible
        self.hud.mode_text.enabled = is_visible
        self.hud.active_cube_text.enabled = is_visible
        self.hud.message_text.enabled = is_visible
        self.hud.reset_button.enabled = is_visible

    # Hàm xử lý khi người chơi bấm nút Slot 1/2/3
    def start_game_from_menu(self, slot: int, is_new_game: bool):
        self.current_slot = slot
        
        if is_new_game:
            target_level = 0
            self.save_manager.save_game(slot, target_level) # Đè file mới
        else:
            target_level = self.save_manager.load_save(slot) # Lọc file cũ
            
        # Nạp map theo level lấy từ file save
        board = self.level_manager.load_level_by_index(target_level)
        self.game_controller.load_board(board)
        
        # Bật lại game view
        self.board_view.root.enabled = True
        self.block_view.root.enabled = True
        self.hud_set_visible(True)
        
        # Set lại camera cho chắc chắn thẳng tâm
        self.setup_camera()

    def setup_camera(self):
        self.center_x = (self.board.cols - 1) / 2
        self.center_z = -(self.board.rows - 1) / 2
        
        board_size = max(self.board.cols, self.board.rows)
        
        # SỬA LẠI 3 DÒNG NÀY ĐỂ ĐẨY CAMERA RA XA HƠN:
        # Tăng mức tối thiểu lên 20 và hệ số nhân lên 1.8 (Bay cao hơn để zoom out)
        self.cam_height = max(20, board_size * 1.8)
        
        # Tăng mức tối thiểu lên 18 và hệ số nhân lên 1.6 (Lùi về phía sau nhiều hơn)
        self.cam_offset_z = max(18, board_size * 1.6)
        
        # Chỉnh lại góc lệch ngang một chút cho cân xứng với độ cao mới
        self.cam_offset_x = self.cam_height * 0.5
        
        # ... (các dòng set position và look_at giữ nguyên như cũ) ...
        camera.position = (
            self.center_x - self.cam_offset_x, 
            self.cam_height, 
            self.center_z - self.cam_offset_z
        )
        camera.look_at(Vec3(self.center_x, 0, self.center_z))
        
    def update_camera_follow(self):
        if not hasattr(self, 'board_view') or not self.board_view.root.enabled:
            return
            
        state = self.game_controller.game.state
        
        if state.mode == BlockMode.NORMAL:
            target_x = state.col
            target_z = -state.row
        else: 
            target_x = (state.cube1[1] + state.cube2[1]) / 2
            target_z = -(state.cube1[0] + state.cube2[0]) / 2

        # TRỌNG TÂM MỚI: Cố định 85% vào giữa map, chỉ nhích 15% theo khối gỗ
        # => Giúp bao trọn map, gần như đứng im, chỉ lướt siêu nhẹ khi khối gỗ di chuyển
        focus_x = self.center_x * 0.85 + target_x * 0.15
        focus_z = self.center_z * 0.85 + target_z * 0.15

        desired_pos = Vec3(
            focus_x - self.cam_offset_x, 
            self.cam_height, 
            focus_z - self.cam_offset_z
        )
        
        # Dùng lerp với tốc độ cực nhỏ (1.5) để camera trôi êm ái, không giật cục
        camera.position = lerp(camera.position, desired_pos, time.dt * 1.5)
        camera.look_at(Vec3(focus_x, 0, focus_z))

    def run(self):
        self.app.run()
        
    def input(self, key):
        self.input_controller.handle_input(key)


if __name__ == "__main__":
    game_app = BloxorzApp()
    game_app.run()