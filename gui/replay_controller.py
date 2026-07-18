from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Callable

from ursina import Entity, time

if TYPE_CHECKING:
    from gui.controller import GameController
    from gui.input_controller import InputController


class ReplayState(str, Enum):
    """
    Trạng thái hiện tại của ReplayController.
    """
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class ReplayController(Entity):
    """
    Phát lại lần lượt các action trong lời giải của solver.

    Trách nhiệm:
    - Đưa game về initial state trước khi replay.
    - Khóa input thủ công trong lúc replay.
    - Gọi GameController.handle_action() theo từng bước.
    - Chờ GameController hoàn tất animation trước khi đi bước tiếp.
    - Hỗ trợ start, stop, pause, resume và thay đổi tốc độ.

    ReplayController không:
    - Tự sửa Game state trực tiếp.
    - Tự cập nhật BoardView, BlockView hoặc HUD.
    - Chạy thuật toán tìm kiếm.

    Mọi action đều đi qua GameController.handle_action() để:
    - cập nhật state,
    - cập nhật bridge,
    - cập nhật block,
    - cập nhật HUD,
    - đếm số bước,
    - xử lý thắng/thua.
    """

    def __init__(
        self,
        game_controller: GameController,
        input_controller: InputController | None = None,
        step_interval: float = 0.38, # Khoảng nghỉ giữa các bước
        initial_delay: float = 0.35, # Khoảng chờ sau khi restart level và trước action đầu tiên.
        on_state_changed: Callable[
            [ReplayState, int, int],
            None
        ] | None = None,
        on_step: Callable[
            [int, int, str],
            None
        ] | None = None,
        on_finished: Callable[[], None] | None = None,
        on_stopped: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None
    ) -> None:
        super().__init__(name="ReplayController")

        if step_interval <= 0:
            raise ValueError(
                "step_interval must be greater than 0."
            )

        if initial_delay < 0:
            raise ValueError(
                "initial_delay must be greater than or equal to 0."
            )
        
        self.game_controller = game_controller
        self.input_controller = input_controller

        # Thời gian giữa hai action liên tiếp.
        self.step_interval = float(step_interval)

        # Thời gian chờ trước action đầu tiên.
        self.initial_delay = float(initial_delay)

        # Báo trạng thái và tiến độ replay thay đổi.
        self.on_state_changed = on_state_changed

        # Báo một action vừa được thực hiện xong.
        self.on_step = on_step

        # Báo replay đã hoàn thành và đến goal.
        self.on_finished = on_finished

        # Báo replay bị người dùng dừng
        self.on_stopped = on_stopped
        self.on_error = on_error

        self.state = ReplayState.IDLE

        # Bản sao path đang được phát.
        # Các action đã được chuẩn hóa thành chữ hoa.
        self._path: list[str] = []

        # Vị trí của action tiếp theo trong self._path.
        # Đồng thời cũng bằng số action đã hoàn thành:
        #   0 -> chưa thực hiện action nào
        #   3 -> đã hoàn thành 3 action
        self._current_index = 0

        # Bộ đếm thời gian tích lũy từ các frame.
        # Mỗi frame cộng thêm time.dt.
        self._elapsed_time = 0.0

        # True khi đang chờ initial_delay trước bước đầu tiên.
        # Sau action đầu tiên, biến này trở thành False
        # và các bước sau dùng step_interval.
        self._waiting_for_first_step = False

        # True sau khi action cuối cùng đã được gửi đi.
        # ReplayController sẽ chờ animation kết thúc,
        # rồi mới kiểm tra game có thật sự thắng hay không.
        self._waiting_for_completion = False

        # Ghi nhớ input trước đó đang bật hay tắt.
        # Khi replay kết thúc, controller khôi phục đúng trạng thái cũ,
        # thay vì lúc nào cũng ép input thành True.
        self._input_was_enabled = True

    
    @property
    def is_replaying(self) -> bool:
        return self.state in {
            ReplayState.RUNNING,
            ReplayState.PAUSED,
        }
    

    @property
    def is_paused(self) -> bool:
        return self.state == ReplayState.PAUSED
    

    @property
    def current_step(self) -> int:
        """
        Số action đã thực hiện thành công.
        Giá trị này cũng chính là index của action tiếp theo.
        """
        return self._current_index
    

    @property
    def total_steps(self) -> int:
        return len(self._path)
    

    @property
    def progress(self) -> float:
        """
        Tỉ lệ hoàn thành replay trong đoạn [0.0, 1.0].
        Ví dụ:
            0.0  -> chưa bắt đầu
            0.5  -> hoàn thành một nửa
            1.0  -> đã thực hiện toàn bộ action
        """
        if not self._path:
            return 0.0
        
        return (
            self._current_index / len(self._path)
        )
    

    def start(self, path: list[str]) -> bool:
        """
        Bắt đầu replay từ đầu level.

        Return:
            True nếu replay được bắt đầu.
            False nếu không thể bắt đầu.
        """
        try:
            normalized_path = self._validate_path(path)

            if self.game_controller.is_animating:
                raise RuntimeError(
                    "Cannot start replay while an animation is running."
                )

            if self.is_replaying:
                self.stop()

            self._lock_game_input()

            # Solver luôn giải từ initial state, nên replay cũng phải
            # bắt đầu lại từ initial state.
            self.game_controller.restart()

            if self.game_controller.is_animating:
                raise RuntimeError(
                    "Game could not restart before replay."
                )

            self._path = normalized_path
            self._current_index = 0
            self._elapsed_time = 0.0
            self._waiting_for_first_step = True
            self._waiting_for_completion = False

            self.state = ReplayState.RUNNING
            self._notify_state_changed()

            # Path rỗng chỉ hợp lệ khi initial state đã là goal.
            if not self._path:
                if self.game_controller.game.is_win():
                    self._finish_success()
                    return True

                raise ValueError(
                    "Replay path is empty but the initial state "
                    "is not the goal."
                )

            return True

        except Exception as error:
            self._fail(error)
            return False
        

    def toggle(self, path: list[str]) -> bool:
        """
        Callback phù hợp trực tiếp với SolverPanel.
        - Chưa replay: bắt đầu phát path.
        - Đang replay: dừng replay.
        """
        if self.is_replaying:
            self.stop()
            return False

        return self.start(path)
    

    def stop(self, reset_level: bool = False) -> None:
        """
        Dừng replay.
        Mặc định giữ block tại state hiện tại.
        reset_level=True sẽ đưa game về đầu level.
        """
        if not self.is_replaying:
            return

        self.state = ReplayState.IDLE
        self._elapsed_time = 0.0
        self._waiting_for_first_step = False
        self._waiting_for_completion = False

        if reset_level and not self.game_controller.is_animating:
            self.game_controller.restart()

        self._restore_game_input()
        self._notify_state_changed()

        if self.on_stopped is not None:
            self.on_stopped()


    def pause(self) -> None:
        if self.state != ReplayState.RUNNING:
            return
        
        self.state = ReplayState.PAUSED
        self._notify_state_changed()

    
    def resume(self) -> None:
        if self.state != ReplayState.PAUSED:
            return

        self.state = ReplayState.RUNNING
        self._notify_state_changed()


    def toggle_pause(self) -> None:
        if self.state == ReplayState.RUNNING:
            self.pause()
        elif self.state == ReplayState.PAUSED:
            self.resume()


    def set_step_interval(self, seconds: float) -> None:
        """
        Thay đổi khoảng nghỉ giữa hai bước replay.
        """
        if seconds <= 0:
            raise ValueError(
                "Replay interval must be greater than 0."
            )

        self.step_interval = float(seconds)


    def update(self) -> None:
        """
        Ursina tự động gọi mỗi frame.
        """
        if self.state != ReplayState.RUNNING:
            return

        # Sau này khi thêm animation lật block, controller chỉ cần
        # đặt is_animating=True. Replay sẽ tự đợi animation kết thúc.
        if self.game_controller.is_animating:
            return

        if self._waiting_for_completion:
            self._finish_after_last_action()
            return

        self._elapsed_time += time.dt

        required_delay = (
            self.initial_delay
            if self._waiting_for_first_step
            else self.step_interval
        )

        if self._elapsed_time < required_delay:
            return

        self._elapsed_time = 0.0
        self._waiting_for_first_step = False

        self._play_next_action()


    def _play_next_action(self) -> None:
        if self._current_index >= len(self._path):
            self._waiting_for_completion = True
            return

        action = self._path[self._current_index]

        moved = self.game_controller.handle_action(
            action
        )

        if not moved:
            self._fail(
                RuntimeError(
                    "Replay action was rejected at "
                    f"step {self._current_index + 1}: "
                    f"{action!r}."
                )
            )
            return

        self._current_index += 1

        if self.on_step is not None:
            self.on_step(
                self._current_index,
                len(self._path),
                action
            )

        self._notify_state_changed()

        if self._current_index >= len(self._path):
            self._waiting_for_completion = True


    def _finish_after_last_action(self) -> None:
        """
        Được gọi sau khi action cuối cùng và animation của nó đã xong.
        """
        if not self.game_controller.game.is_win():
            self._fail(
                RuntimeError(
                    "Replay path ended but the game did not reach "
                    "the goal state."
                )
            )
            return

        self._finish_success()


    def _finish_success(self) -> None:
        self.state = ReplayState.IDLE
        self._elapsed_time = 0.0
        self._waiting_for_first_step = False
        self._waiting_for_completion = False

        self._restore_game_input()
        self._notify_state_changed()

        if self.on_finished is not None:
            self.on_finished()


    def _fail(self, error: Exception) -> None:
        self.state = ReplayState.IDLE
        self._elapsed_time = 0.0
        self._waiting_for_first_step = False
        self._waiting_for_completion = False

        self._restore_game_input()
        self._notify_state_changed()

        if self.on_error is not None:
            self.on_error(error)
            return

        # Không nuốt lỗi hoàn toàn: vẫn in ra terminal để debug,
        # nhưng không làm crash vòng lặp Ursina.
        print(f"[ReplayController] {error}")


    def _lock_game_input(self) -> None:
        if self.input_controller is None:
            return

        self._input_was_enabled = (
            self.input_controller.enabled
        )
        self.input_controller.enabled = False


    def _restore_game_input(self) -> None:
        if self.input_controller is None:
            return

        self.input_controller.enabled = (
            self._input_was_enabled
        )


    def _notify_state_changed(self) -> None:
        if self.on_state_changed is None:
            return

        self.on_state_changed(
            self.state,
            self._current_index,
            len(self._path)
        )


    @staticmethod
    def _validate_path(path: list[str]) -> list[str]:
        if not isinstance(path, list):
            raise TypeError(
                "Replay path must be a list of action strings."
            )

        normalized_path: list[str] = []

        for index, action in enumerate(path):
            if not isinstance(action, str):
                raise TypeError(
                    "Replay action at index "
                    f"{index} must be a string."
                )

            normalized_action = action.strip().upper()

            if not normalized_action:
                raise ValueError(
                    "Replay action at index "
                    f"{index} must not be empty."
                )

            normalized_path.append(
                normalized_action
            )

        return normalized_path