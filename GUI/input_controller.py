from core.block import UP, DOWN, LEFT, RIGHT
from core.game import SWITCH_CUBE


class InputController:
    def __init__(self, game_controller, level_manager=None):
        self.game_controller = game_controller
        self.level_manager = level_manager

        self.keymap = {
            "w": UP,
            "arrow up": UP,

            "s": DOWN,
            "arrow down": DOWN,

            "a": LEFT,
            "arrow left": LEFT,

            "d": RIGHT,
            "arrow right": RIGHT,

            "space": SWITCH_CUBE,
        }

    def handle_input(self, key: str):
        key = key.lower()

        if key in self.keymap:
            action = self.keymap[key]
            self.game_controller.handle_action(action)
            return

        if key == "r":
            self.game_controller.reset()
            return

        if key == "n":
            self.load_next_level()
            return

        if key == "p":
            self.load_previous_level()
            return

    def load_next_level(self):
        if self.level_manager is None:
            return

        board = self.level_manager.next_level()
        self.game_controller.load_board(board)

    def load_previous_level(self):
        if self.level_manager is None:
            return

        board = self.level_manager.previous_level()
        self.game_controller.load_board(board)