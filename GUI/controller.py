from core.game import Game
from ursina import Audio
from ursina import Audio, invoke
from solvers.bfs import solve as bfs_solve
from solvers.ids import solve as ids_solve
from solvers.ucs import solve as ucs_solve
from solvers.astar import solve as astar_solve

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
        self.block_view.clear_block()
        self.refresh_views()

    def load_board(self, board):
        if self.input_locked:
            return

        self.board = board
        self.game = Game(board)
        self.move_count = 0
        self.is_finished = False
        self.block_view.clear_block()
        self.board_view.load_board(board)
        self.refresh_views()

    def run_auto_solver(self, algorithm_name: str):
        if self.is_finished:
            return

        self.input_locked = False
        self.reset()
        self.input_locked = True 
        
        if self.hud is not None:
            self.hud.path_text.text = f"AI {algorithm_name}: Đang tính toán... (Vui lòng chờ)"
            
        invoke(self._process_solver, algorithm_name, delay=0.1)

    def _process_solver(self, algorithm_name: str):
        try:
            result = None
            if algorithm_name == "BFS":
                result = bfs_solve(self.game)
            elif algorithm_name == "IDS":
                result = ids_solve(self.game)
            elif algorithm_name == "UCS":
                result = ucs_solve(self.game)
            elif algorithm_name == "A*":
                result = astar_solve(self.game)

            if result is None or result.path is None:
                if self.hud is not None:
                    self.hud.path_text.text = f"AI {algorithm_name}: Không tìm thấy đường!"
                self.input_locked = False
                return

            actions_list = result.path

            if self.hud is not None:
                self.hud.path_text.text = (
                    f"--- {algorithm_name} ---\n"
                    f"Time: {result.search_time:.4f}s\n"
                    f"Nodes: {result.expanded_nodes}\n"
                    f"Total Steps: {result.solution_length}"
                )

            # Bắt đầu tự động lăn khối gỗ
            self.execute_steps_one_by_one(actions_list, 0)
            
        except Exception as e:
            if self.hud is not None:
                self.hud.path_text.text = f"BÁO LỖI: {str(e)}"
            self.input_locked = False


    def execute_steps_one_by_one(self, actions, index):
        # Nếu đã đi hết danh sách các bước do AI vạch ra hoặc lỡ rơi ra ngoài
        if index >= len(actions) or self.is_finished:
            self.input_locked = False # Mở khóa phím trả lại cho người chơi
            return

        # Lấy hành động hiện tại ra (UP, DOWN, LEFT, RIGHT...)
        current_action = actions[index]
        
        # Mở khóa tạm thời để hàm handle_action cho phép khối gỗ lăn
        self.input_locked = False
        self.handle_action(current_action)
        self.input_locked = True # Khóa lại ngay lập tức để chờ bước tiếp theo

        # Gọi lại chính nó sau 0.3 giây (Tạo độ trễ để người chơi nhìn rõ khối gỗ lật)
        invoke(self.execute_steps_one_by_one, actions, index + 1, delay=0.3)