from core.game import Game
from ursina import Audio

class GameController:
    def __init__(
        self,
        board,
        board_view,
        block_view,
        hud=None,
        animation_controller=None,
    ):
        self.board = board
        self.game = Game(board)

        self.board_view = board_view
        self.block_view = block_view
        self.hud = hud
        self.animation_controller = animation_controller

        self.move_count = 0
        self.is_finished = False
        self.input_locked = False

        self.move_sound = Audio('../assets/move.ogg', autoplay=False, volume = 1.5)
        self.win_sound = Audio('../assets/win.ogg', autoplay=False,volume = 0.2)
        
        self.bg_music = Audio('../assets/bgm.ogg', loop=True, autoplay=True, volume=0.3)

        self.refresh_views()

    def handle_action(self, action: str):
        if self.input_locked:
            return False

        if self.is_finished:
            return False

        old_state = self.game.state
        moved = self.game.move(action)

        if not moved:
            return False

        self.move_sound.play()

        self.move_count += 1
        new_state = self.game.state

        self.after_state_changed(old_state, new_state)

        if self.game.is_win():
            self.handle_win()

        return True

    def after_state_changed(self, old_state, new_state):
        if self.animation_controller is not None:
            self.play_animation(old_state, new_state)
        else:
            self.refresh_views()

    def play_animation(self, old_state, new_state):
        self.input_locked = True

        self.animation_controller.play_move(
            old_state=old_state,
            new_state=new_state,
            on_complete=self.on_animation_complete,
        )

    def on_animation_complete(self):
        self.input_locked = False
        self.refresh_views()

    def refresh_views(self):
        self.board_view.update(self.game.state)
        self.block_view.update(self.game.state)

        if self.hud is not None:
            self.hud.update(
                board=self.board,
                state=self.game.state,
                move_count=self.move_count,
                is_finished=self.is_finished,
            )

    def handle_win(self):
        self.is_finished = True

        self.win_sound.play()

        self.refresh_views()

        if self.hud is not None:
            self.hud.show_message("You win!")

    def reset(self):
        if self.input_locked:
            return

        self.game = Game(self.board)
        self.move_count = 0
        self.is_finished = False

        self.refresh_views()

    def load_board(self, board):
        if self.input_locked:
            return

        self.board = board
        self.game = Game(board)
        self.move_count = 0
        self.is_finished = False

        self.board_view.load_board(board)
        self.refresh_views()
