from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from core.game import Game, SWITCH_CUBE
from core.move_result import MoveResult, MoveStatus
from core.state import BlockMode

if TYPE_CHECKING:
    from core.board import Board
    from core.state import State
    from gui.views.board import BoardView
    from gui.views.block import BlockView
    from gui.views.hud import HUD
    from gui.audio_manager import AudioManager


class GameController:
    """
    Điều phối Game logic, GUI và animation.

    Game.try_move() quyết định state trước.
    GameController sau đó phát animation từ previous_state
    đến resulting_state/attempted_state và khóa input bằng is_animating.
    """

    def __init__(
        self,
        board: Board,
        board_view: BoardView,
        block_view: BlockView,
        hud: HUD | None = None,
        audio_manager: AudioManager | None = None
    ) -> None:
        self.board_view = board_view
        self.block_view = block_view
        self.hud = hud
        self.audio_manager = audio_manager

        self.board: Board
        self.game: Game

        self.move_count = 0
        self.is_finished = False
        self.is_animating = False

        # App dùng callback này để hiển thị completion screen
        # sau khi block đã chìm hoàn toàn vào Goal.
        self.on_level_completed: Callable[[int], None] | None = None

        self.load_board(board)

    def handle_action(self, action: str) -> bool:
        """
        Thực hiện action và phát animation tương ứng.

        Return:
            True khi action là MOVED, WON hoặc LOST.
            False khi action bị IGNORED hoặc controller đang bận.
        """
        if self.is_finished or self.is_animating:
            return False

        result = self.game.try_move(action)

        if result.status == MoveStatus.IGNORED:
            return False

        # Một action dẫn đến rơi vẫn được tính là một bước.
        self.move_count += 1

        if result.status in {
            MoveStatus.MOVED,
            MoveStatus.WON,
        }:
            self._start_successful_move_animation(
                result=result,
                action=action
            )
            return True

        if result.status == MoveStatus.LOST:
            self._start_loss_animation(
                result=result,
                action=action
            )
            return True

        raise RuntimeError(
            f"Unsupported move status: {result.status}"
        )

    def _start_successful_move_animation(
        self,
        result: MoveResult,
        action: str
    ) -> None:
        resulting_state = result.resulting_state

        if resulting_state is None:
            raise RuntimeError(
                "MOVED/WON result requires resulting_state."
            )

        move_won = (
            result.status == MoveStatus.WON
        )

        self.is_finished = move_won
        self.is_animating = True

        # HUD tăng move count ngay, nhưng giữ orientation cũ
        # cho đến khi animation block kết thúc.
        self._update_hud_during_animation(
            result.previous_state
        )

        def finish_move() -> None:
            # Âm block_move là tiếng chạm tile ngắn nên phát đúng lúc
            # rotate animation vừa kết thúc.
            self._play_landing_sound(
                action
            )

            # Switch và bridge chỉ đổi hình ảnh sau khi block chạm đất.
            self.board_view.update(
                resulting_state
            )

            self._play_state_change_sounds(
                previous_state=result.previous_state,
                resulting_state=resulting_state
            )

            if move_won:
                # Giữ is_animating=True trong toàn bộ goal animation.
                # Input và replay sẽ tự chờ block chìm hoàn tất.
                self.block_view.play_goal_drop(
                    goal_state=resulting_state,
                    on_drop_started=self._play_goal_drop_sound,
                    on_complete=self._finish_win_animation
                )
                return

            self.is_animating = False

            self.refresh_views(
                update_block=False
            )

        self.block_view.play_move(
            previous_state=result.previous_state,
            resulting_state=resulting_state,
            action=action,
            on_complete=finish_move
        )



    def _play_landing_sound(
        self,
        action: str
    ) -> None:
        if self.audio_manager is None:
            return

        normalized_action = action.strip().upper()

        # Space/SWITCH chỉ đổi active cube, không có block landing.
        if normalized_action in {
            SWITCH_CUBE,
            "SPACE"
        }:
            return

        self.audio_manager.play_block_move()


    def _play_state_change_sounds(
        self,
        previous_state: State,
        resulting_state: State
    ) -> None:
        if self.audio_manager is None:
            return

        bridges_changed = (
            previous_state.bridges
            != resulting_state.bridges
        )

        split_switch_activated = (
            previous_state.mode == BlockMode.NORMAL
            and resulting_state.mode == BlockMode.SPLIT
        )

        if bridges_changed or split_switch_activated:
            self.audio_manager.play_switch()

        if bridges_changed:
            self.audio_manager.play_bridge()


    def _play_goal_drop_sound(self) -> None:
        if self.audio_manager is not None:
            self.audio_manager.play_goal_drop()


    def _play_fall_sound(self) -> None:
        if self.audio_manager is not None:
            self.audio_manager.play_fall()


    def set_level_completed_callback(
        self,
        callback: Callable[[int], None] | None
    ) -> None:
        """
        Gán callback được gọi sau khi goal-drop animation kết thúc.

        Callback nhận move_count của level vừa hoàn thành.
        """
        if callback is not None and not callable(callback):
            raise TypeError(
                "level completed callback must be callable or None."
            )

        self.on_level_completed = callback


    def _finish_win_animation(self) -> None:
        """
        Hoàn tất chiến thắng sau khi block đã chìm vào Goal.
        """
        self.is_animating = False

        if self.audio_manager is not None:
            self.audio_manager.play_victory()

        # Block đang bị ẩn dưới Goal nên không update BlockView.
        # Board, HUD và Solver statistics vẫn được giữ nguyên.
        self.refresh_views(
            update_block=False
        )

        if self.on_level_completed is not None:
            self.on_level_completed(
                self.move_count
            )
            return

        if self.hud is not None:
            self.hud.show_message(
                "Stage Complete!\\nPress N for next level"
            )


    def _start_loss_animation(
        self,
        result: MoveResult,
        action: str
    ) -> None:
        self.is_finished = True
        self.is_animating = True

        self._update_hud_during_animation(
            result.previous_state
        )

        attempted_state = result.attempted_state

        if attempted_state is None:
            self._finish_loss()
            return

        def start_failure_effect() -> None:
            self._play_landing_sound(
                action
            )

            # Chỉ kích hoạt thay đổi bridge/switch sau khi block đã lăn
            # đến vị trí attempted_state.
            self.board_view.update(
                attempted_state
            )

            self._play_state_change_sounds(
                previous_state=result.previous_state,
                resulting_state=attempted_state
            )

            if result.reason == "standing_on_fragile":
                self._play_fragile_failure(
                    attempted_state
                )
                return

            self._play_fall_sound()

            self.block_view.play_fall(
                attempted_state=attempted_state,
                on_complete=self._finish_loss
            )

        # Trước khi rơi, block/cube vẫn lăn đến vị trí nước đi thất bại.
        self.block_view.play_move(
            previous_state=result.previous_state,
            resulting_state=attempted_state,
            action=action,
            on_complete=start_failure_effect
        )

    def _play_fragile_failure(
        self,
        attempted_state: State
    ) -> None:
        """
        Sau khi block đã lăn và đứng trên fragile tile:
        tile vỡ trước, block rơi sau.
        """
        def start_block_fall() -> None:
            self._play_fall_sound()

            self.block_view.play_fall(
                attempted_state=attempted_state,
                on_complete=self._finish_loss
            )

        self.board_view.play_fragile_break(
            row=attempted_state.row,
            col=attempted_state.col,
            on_complete=start_block_fall
        )

    def _update_hud_during_animation(
        self,
        state: State
    ) -> None:
        if self.hud is None:
            return

        self.hud.update(
            board=self.board,
            state=state,
            move_count=self.move_count,
            is_finished=False
        )

    def restart(self) -> None:
        """
        Khởi động lại level hiện tại.

        Không restart khi animation vẫn đang chạy.
        """
        if self.is_animating:
            return

        self.game = Game(self.board)
        self.move_count = 0
        self.is_finished = False
        self.is_animating = False

        self.board_view.reset_fragile_tiles()

        if self.hud is not None:
            self.hud.clear_message()

        self.refresh_views()

    def load_board(self, board: Board) -> None:
        self.board = board
        self.game = Game(board)

        self.move_count = 0
        self.is_finished = False
        self.is_animating = False

        self.board_view.load_board(board)

        if self.hud is not None:
            self.hud.show_message("")

        self.refresh_views()

    def refresh_views(
        self,
        update_block: bool = True
    ) -> None:
        """
        Đồng bộ GUI với Game state.

        update_block=False được dùng ngay sau rotate animation vì
        BlockView đã ở đúng state với quaternion vật lý tích lũy.
        """
        state = self.game.state

        self.board_view.update(state)

        if update_block:
            self.block_view.update(state)

        if self.hud is not None:
            self.hud.update(
                board=self.board,
                state=state,
                move_count=self.move_count,
                is_finished=self.is_finished
            )

    def _finish_loss(self) -> None:
        self.is_animating = False

        if self.hud is not None:
            self.hud.show_failed_status()
            self.hud.show_message(
                "You lose!\nPress R to restart"
            )