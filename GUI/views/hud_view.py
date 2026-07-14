from ursina import (
    Text,
    Button,
    color,
    camera,
)

from core.state import BlockMode


class HUD:
    def __init__(self, game_controller=None):
        self.game_controller = game_controller

        self.level_text = Text(
            text="Level: -",
            parent=camera.ui,
            position=(-0.86, 0.45),
            scale=1.2,
            color=color.white,
        )

        self.move_text = Text(
            text="Moves: 0",
            parent=camera.ui,
            position=(-0.86, 0.39),
            scale=1.2,
            color=color.white,
        )

        self.mode_text = Text(
            text="Mode: normal",
            parent=camera.ui,
            position=(-0.86, 0.33),
            scale=1.2,
            color=color.white,
        )

        self.active_cube_text = Text(
            text="",
            parent=camera.ui,
            position=(-0.86, 0.27),
            scale=1.2,
            color=color.azure,
        )

        self.message_text = Text(
            text="",
            parent=camera.ui,
            position=(-0.15, 0.38),
            scale=2,
            color=color.yellow,
        )

        self.reset_button = Button(
            text="Reset",
            parent=camera.ui,
            position=(0.72, 0.43),
            scale=(0.16, 0.06),
            color=color.dark_gray,
            text_color=color.white,
        )

        self.reset_button.on_click = self.on_reset_clicked

        self.path_text = Text(
            text="", 
            parent=camera.ui,
            position=(-0.86, 0.10),
            scale=1,
            color=color.yellow, 
            
        )

        # Dùng tên màu có sẵn để tránh lỗi trắng bóc
        self.btn_bfs = Button(
            text="BFS", parent=camera.ui,
            position=(0.72, 0.35), scale=(0.16, 0.05),
            color=color.green, text_color=color.white,
            on_click=lambda: self.trigger_solver("BFS")
        )

        self.btn_ids = Button(
            text="IDS", parent=camera.ui,
            position=(0.72, 0.29), scale=(0.16, 0.05),
            color=color.orange, text_color=color.white,
            on_click=lambda: self.trigger_solver("IDS")
        )

        self.btn_ucs = Button(
            text="UCS", parent=camera.ui,
            position=(0.72, 0.23), scale=(0.16, 0.05),
            color=color.magenta, text_color=color.white,
            on_click=lambda: self.trigger_solver("UCS")
        )

        self.btn_astar = Button(
            text="A*", parent=camera.ui,
            position=(0.72, 0.17), scale=(0.16, 0.05),
            color=color.azure, text_color=color.black,
            on_click=lambda: self.trigger_solver("A*")
        )

    def set_game_controller(self, game_controller):
        self.game_controller = game_controller

    def trigger_solver(self, algorithm_name):
        if self.game_controller is not None:
            self.game_controller.run_auto_solver(algorithm_name)

    def set_game_controller(self, game_controller):
        self.game_controller = game_controller

    def update(self, board, state, move_count: int, is_finished: bool):
        self.level_text.text = f"Level: {board.name}"
        self.move_text.text = f"Moves: {move_count}"

        if state.mode == BlockMode.NORMAL:
            self.mode_text.text = f"Mode: {state.mode.value}"
            self.active_cube_text.text = ""

        elif state.mode == BlockMode.SPLIT:
            self.mode_text.text = f"Mode: {state.mode.value}"
            self.active_cube_text.text = f"Active cube: {state.active_cube}"

        if is_finished:
            self.show_message("You win!")
        else:
            self.clear_message()

    def show_message(self, message: str):
        self.message_text.text = message
        self.message_text.enabled = True

    def clear_message(self):
        self.message_text.text = ""

    def on_reset_clicked(self):
        if self.game_controller is not None:
            self.game_controller.reset()