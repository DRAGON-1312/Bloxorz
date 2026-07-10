from ursina import (
    Ursina,
    EditorCamera,
    window,
    camera,
    Vec3,
)
from core.level_loader import load_level
from core.game import Game
from GUI.level_manager import LevelManager
from GUI.views.board_view import BoardView
from GUI.views.block_view import BlockView
from GUI.controller import GameController
from GUI.input_controller import InputController
from GUI.views.hud_view import HUD


class BloxorzApp:
    def __init__(self):
        self.app = Ursina()

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
        
        self.setup_window()
        self.setup_camera()

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
    
    def setup_camera(self):
        center_x = (self.board.cols - 1) / 2
        center_z = -(self.board.rows - 1) / 2

        camera.position = (center_x - 15, 10, center_z - 10)
        camera.look_at(Vec3(10,-2,-2))

        # EditorCamera()

    def run(self):
        self.app.run()
        
    def input(self, key):
        self.input_controller.handle_input(key)


if __name__ == "__main__":
    game_app = BloxorzApp()
    game_app.run()