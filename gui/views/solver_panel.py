from __future__ import annotations

from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING, Callable

from ursina import Button, Entity, Text, camera, color, window

from gui.solver_controller import SolverAlgorithm, SolverController

if TYPE_CHECKING:
    from gui.input_controller import InputController
    from solvers.result import SearchResult


class SolverPanel(Entity):
    """
    Panel điều khiển solver trong cùng cửa sổ Ursina.

    Trách nhiệm:
    - Cho người dùng chọn BFS, IDS, UCS hoặc A*.
    - Chạy solver ở background thread để GUI không bị đứng.
    - Hiển thị các số liệu tìm kiếm.
    - Hiển thị một phần đường đi tìm được.
    - Chuẩn bị nút Replay để nối với ReplayController sau này.
    """

    PANEL_COLOR = color.rgba32(18, 20, 26, 225)
    BUTTON_COLOR = color.rgb32(55, 70, 90)
    BUTTON_HIGHLIGHT = color.rgb32(80, 105, 135)
    BUTTON_PRESSED = color.rgb32(40, 50, 70)
    SELECTED_COLOR = color.rgb32(195, 120, 55)
    TEXT_COLOR = color.rgb32(235, 238, 245)
    MUTED_TEXT_COLOR = color.rgb32(175, 185, 200)
    SUCCESS_COLOR = color.rgb32(130, 220, 150)
    WARNING_COLOR = color.rgb32(255, 210, 90)
    ERROR_COLOR = color.rgb32(235, 95, 95)

    def __init__(
        self,
        solver_controller: SolverController,
        input_controller: InputController | None = None,
        on_result: Callable[[SolverAlgorithm, SearchResult], None] | None = None,
        on_replay: Callable[[list[str]], None] | None = None,
        start_open: bool = False
    ) -> None:
        super().__init__(parent=camera.ui, name="SolverPanelRoot")

        # camera.ui không có biên phải cố định là 1.0.
        # Với tỉ lệ màn hình 1.6, biên phải chỉ khoảng 0.8.
        # Vì vậy toàn bộ panel phải được căn theo window.aspect_ratio.
        self.ui_right = window.aspect_ratio / 2
        self.panel_width = 0.34
        self.panel_margin = 0.015

        self.panel_right_x = (
            self.ui_right - self.panel_margin
        )
        self.panel_left_x = (
            self.panel_right_x - self.panel_width
        )
        self.panel_center_x = (
            self.panel_left_x + self.panel_width / 2
        )
        self.content_left_x = (
            self.panel_left_x + 0.025
        )
        self.content_right_x = (
            self.panel_right_x - 0.025
        )

        self.solver_controller = solver_controller
        self.input_controller = input_controller
        self.on_result = on_result
        self.on_replay = on_replay

        self.selected_algorithm = SolverAlgorithm.BFS
        self.is_busy = False
        self.last_result: SearchResult | None = None

        self._input_was_enabled = True
        self._worker_thread: Thread | None = None
        self._result_queue: Queue[tuple[str, object]] = Queue()

        self._panel_items: list[Entity] = []
        self.algorithm_buttons: dict[SolverAlgorithm, Button] = {}

        self._build_toggle_button()
        self._build_panel()

        self.set_open(start_open)
        self._refresh_algorithm_buttons()
        self._set_replay_available(False)

    def _build_toggle_button(self) -> None:
        self.toggle_button = Button(
            parent=self,
            name="SolverToggleButton",
            text="Solver",
            position=(
                self.panel_right_x - 0.06,
                0.46
            ),
            scale=(0.12, 0.05),
            color=self.BUTTON_COLOR,
            highlight_color=self.BUTTON_HIGHLIGHT,
            pressed_color=self.BUTTON_PRESSED,
            text_color=color.white,
            on_click=self.toggle
        )

    def _build_panel(self) -> None:
        self.background = Entity(
            parent=self,
            name="SolverPanelBackground",
            model="quad",
            texture="white_cube",
            position=(self.panel_center_x, 0.02),
            scale=(self.panel_width, 0.84),
            color=self.PANEL_COLOR
        )
        self._panel_items.append(self.background)

        self.title_text = Text(
            parent=self,
            name="SolverTitleText",
            text="Solver",
            position=(self.content_left_x, 0.43),
            origin=(-0.5, 0.5),
            scale=1.05,
            color=self.TEXT_COLOR
        )
        self._panel_items.append(self.title_text)

        self.source_text = Text(
            parent=self,
            name="SolverSourceText",
            text="Solve from: Level Start",
            position=(self.content_left_x, 0.385),
            origin=(-0.5, 0.5),
            scale=0.70,
            color=self.MUTED_TEXT_COLOR
        )
        self._panel_items.append(self.source_text)

        self._build_algorithm_buttons()

        self.solve_button = Button(
            parent=self,
            name="SolveButton",
            text="Solve",
            position=(
                self.content_left_x + 0.065,
                0.27
            ),
            scale=(0.13, 0.055),
            color=color.rgb32(45, 125, 80),
            highlight_color=color.rgb32(65, 155, 105),
            pressed_color=color.rgb32(35, 95, 65),
            text_color=color.white,
            on_click=self.solve_selected
        )
        self._panel_items.append(self.solve_button)

        self.replay_button = Button(
            parent=self,
            name="ReplayButton",
            text="Replay",
            position=(
                self.content_right_x - 0.065,
                0.27
            ),
            scale=(0.13, 0.055),
            color=self.BUTTON_COLOR,
            highlight_color=self.BUTTON_HIGHLIGHT,
            pressed_color=self.BUTTON_PRESSED,
            text_color=color.white,
            on_click=self.replay_last_result
        )
        self._panel_items.append(self.replay_button)

        self.status_text = Text(
            parent=self,
            name="SolverStatusText",
            text="Status: Ready",
            position=(self.content_left_x, 0.215),
            origin=(-0.5, 0.5),
            scale=0.72,
            color=self.SUCCESS_COLOR
        )
        self._panel_items.append(self.status_text)

        self.algorithm_text = self._make_text(
            "SolverAlgorithmText", "Algorithm: BFS", 0.165
        )
        self.time_text = self._make_text(
            "SolverTimeText", "Search time: --", 0.125
        )
        self.memory_text = self._make_text(
            "SolverMemoryText", "Peak memory: --", 0.085
        )
        self.expanded_text = self._make_text(
            "SolverExpandedText", "Expanded nodes: --", 0.045
        )
        self.length_text = self._make_text(
            "SolverLengthText", "Solution length: --", 0.005
        )
        self.cost_text = self._make_text(
            "SolverCostText", "Solution cost: --", -0.035
        )

        self.path_label = Text(
            parent=self,
            name="SolverPathLabel",
            text="Path:",
            position=(self.content_left_x, -0.095),
            origin=(-0.5, 0.5),
            scale=0.70,
            color=self.TEXT_COLOR
        )
        self._panel_items.append(self.path_label)

        self.path_text = Text(
            parent=self,
            name="SolverPathText",
            text="--",
            position=(self.content_left_x, -0.135),
            origin=(-0.5, 0.5),
            scale=0.58,
            color=self.MUTED_TEXT_COLOR
        )
        self._panel_items.append(self.path_text)

        self.note_text = Text(
            parent=self,
            name="SolverNoteText",
            text="Replay will be connected next.",
            position=(self.content_left_x, -0.34),
            origin=(-0.5, 0.5),
            scale=0.58,
            color=self.MUTED_TEXT_COLOR
        )
        self._panel_items.append(self.note_text)

    def _make_text(self, name: str, text: str, y: float) -> Text:
        text_entity = Text(
            parent=self,
            name=name,
            text=text,
            position=(self.content_left_x, y),
            origin=(-0.5, 0.5),
            scale=0.68,
            color=self.TEXT_COLOR
        )
        self._panel_items.append(text_entity)
        return text_entity

    def _build_algorithm_buttons(self) -> None:
        """
        Tạo bốn nút thuật toán và tự dàn đều trong chiều rộng panel.
        """
        algorithms = [
            SolverAlgorithm.BFS,
            SolverAlgorithm.IDS,
            SolverAlgorithm.UCS,
            SolverAlgorithm.ASTAR,
        ]

        button_width = 0.062
        available_width = (
            self.content_right_x
            - self.content_left_x
        )

        total_button_width = (
            button_width * len(algorithms)
        )

        gap = (
            available_width - total_button_width
        ) / (len(algorithms) - 1)

        for index, algorithm in enumerate(algorithms):
            x_position = (
                self.content_left_x
                + button_width / 2
                + index * (button_width + gap)
            )

            button = Button(
                parent=self,
                name=f"{algorithm.name}Button",
                text=algorithm.value,
                position=(x_position, 0.33),
                scale=(button_width, 0.047),
                color=self.BUTTON_COLOR,
                highlight_color=self.BUTTON_HIGHLIGHT,
                pressed_color=self.BUTTON_PRESSED,
                text_color=color.white,
                on_click=(
                    lambda selected=algorithm:
                    self.select_algorithm(selected)
                )
            )

            self.algorithm_buttons[algorithm] = button
            self._panel_items.append(button)

    def update(self) -> None:
        """
        Ursina gọi mỗi frame. Kết quả worker được xử lý ở main thread.
        """
        while True:
            try:
                message_type, payload = self._result_queue.get_nowait()
            except Empty:
                break

            if message_type == "result":
                self._finish_success(payload)
            elif message_type == "error":
                self._finish_error(payload)
            else:
                self._finish_error(
                    RuntimeError(f"Unknown worker message: {message_type}")
                )

    def toggle(self) -> None:
        self.set_open(not self.background.enabled)

    def set_open(self, is_open: bool) -> None:
        for item in self._panel_items:
            item.enabled = is_open

        self.toggle_button.text = "Close" if is_open else "Solver"

    def select_algorithm(self, algorithm: SolverAlgorithm | str) -> None:
        if self.is_busy:
            return

        self.selected_algorithm = self.solver_controller.normalize_algorithm(
            algorithm
        )
        self.algorithm_text.text = (
            f"Algorithm: {self.selected_algorithm.value}"
        )
        self._refresh_algorithm_buttons()

    def solve_selected(self) -> None:
        """
        Chạy thuật toán đang chọn trong daemon thread.
        """
        if self.is_busy:
            return

        if self.solver_controller.is_solving:
            self._show_status(
                "Status: Solver is already running",
                self.WARNING_COLOR
            )
            return

        self.is_busy = True
        self.last_result = None
        self._set_replay_available(False)
        self._clear_statistics()

        self.solve_button.text = "Solving..."
        self._show_status(
            f"Status: Running {self.selected_algorithm.value}...",
            self.WARNING_COLOR
        )
        self._lock_game_input()

        while True:
            try:
                self._result_queue.get_nowait()
            except Empty:
                break

        selected_algorithm = self.selected_algorithm
        self._worker_thread = Thread(
            target=self._solver_worker,
            args=(selected_algorithm,),
            name=f"{selected_algorithm.name}SolverThread",
            daemon=True
        )
        self._worker_thread.start()

    def _solver_worker(self, algorithm: SolverAlgorithm) -> None:
        """
        Không chỉnh Ursina Entity trực tiếp trong worker thread.
        """
        try:
            result = self.solver_controller.solve_current_level(algorithm)
        except Exception as error:
            self._result_queue.put(("error", error))
        else:
            self._result_queue.put(("result", (algorithm, result)))

    def _finish_success(self, payload: object) -> None:
        algorithm, result = payload

        self.is_busy = False
        self.last_result = result
        self.solve_button.text = "Solve"
        self._restore_game_input()

        if result.path is None:
            self._show_status(
                "Status: No solution found",
                self.WARNING_COLOR
            )
            self._set_replay_available(False)
        else:
            self._show_status(
                "Status: Solution found",
                self.SUCCESS_COLOR
            )
            self._set_replay_available(True)

        self._show_result(algorithm, result)

        if self.on_result is not None:
            self.on_result(algorithm, result)

    def _finish_error(self, payload: object) -> None:
        self.is_busy = False
        self.last_result = None
        self.solve_button.text = "Solve"
        self._restore_game_input()
        self._set_replay_available(False)

        error_message = str(payload).strip() or type(payload).__name__
        self._show_status(
            f"Error: {error_message}",
            self.ERROR_COLOR
        )

    def _show_result(
        self,
        algorithm: SolverAlgorithm,
        result: SearchResult
    ) -> None:
        self.algorithm_text.text = f"Algorithm: {algorithm.value}"
        self.time_text.text = f"Search time: {result.search_time:.6f} s"
        self.memory_text.text = (
            f"Peak memory: {self._format_memory(result.memory_usage)}"
        )
        self.expanded_text.text = (
            f"Expanded nodes: {result.expanded_nodes:,}"
        )
        self.length_text.text = (
            "Solution length: "
            f"{self._format_optional(result.solution_length)}"
        )
        self.cost_text.text = (
            "Solution cost: "
            f"{self._format_optional(result.solution_cost)}"
        )
        self.path_text.text = self._format_path(result.path)

    def replay_last_result(self) -> None:
        if self.is_busy:
            return

        result = self.last_result

        if result is None or result.path is None:
            self._show_status(
                "Status: Solve a level first",
                self.WARNING_COLOR
            )
            return

        if self.on_replay is None:
            self._show_status(
                "Status: Replay is not connected yet",
                self.WARNING_COLOR
            )
            return

        self.on_replay(list(result.path))

    def clear_result(self) -> None:
        """
        Xóa path và statistics cũ khi đổi level.
        """
        if self.is_busy:
            return

        self.last_result = None
        self.solver_controller.clear_last_result()
        self.algorithm_text.text = (
            f"Algorithm: {self.selected_algorithm.value}"
        )
        self._clear_statistics()
        self._show_status("Status: Ready", self.SUCCESS_COLOR)
        self._set_replay_available(False)

    def set_replay_callback(
        self,
        callback: Callable[[list[str]], None] | None
    ) -> None:
        if callback is not None and not callable(callback):
            raise TypeError("Replay callback must be callable or None.")

        self.on_replay = callback
        self._set_replay_available(
            self.last_result is not None
            and self.last_result.path is not None
        )

    def _clear_statistics(self) -> None:
        self.time_text.text = "Search time: --"
        self.memory_text.text = "Peak memory: --"
        self.expanded_text.text = "Expanded nodes: --"
        self.length_text.text = "Solution length: --"
        self.cost_text.text = "Solution cost: --"
        self.path_text.text = "--"

    def _show_status(self, message: str, text_color) -> None:
        self.status_text.text = message
        self.status_text.color = text_color

    def _refresh_algorithm_buttons(self) -> None:
        for algorithm, button in self.algorithm_buttons.items():
            button.color = (
                self.SELECTED_COLOR
                if algorithm == self.selected_algorithm
                else self.BUTTON_COLOR
            )

    def _set_replay_available(self, is_available: bool) -> None:
        self.replay_button.color = (
            color.rgb32(55, 105, 145)
            if is_available
            else color.rgb32(65, 68, 75)
        )

    def _lock_game_input(self) -> None:
        if self.input_controller is None:
            return

        self._input_was_enabled = self.input_controller.enabled
        self.input_controller.enabled = False

    def _restore_game_input(self) -> None:
        if self.input_controller is None:
            return

        self.input_controller.enabled = self._input_was_enabled

    @staticmethod
    def _format_memory(memory_bytes: int) -> str:
        if memory_bytes < 1024:
            return f"{memory_bytes} B"

        memory_kb = memory_bytes / 1024

        if memory_kb < 1024:
            return f"{memory_kb:.2f} KB"

        return f"{memory_kb / 1024:.2f} MB"

    @staticmethod
    def _format_optional(value) -> str:
        return "--" if value is None else str(value)

    @staticmethod
    def _format_path(
        path: list[str] | None,
        max_actions: int = 12,
        actions_per_line: int = 4
    ) -> str:
        if path is None:
            return "No solution"

        if not path:
            return "(already at goal)"

        shown_actions = path[:max_actions]
        lines = []

        for start in range(0, len(shown_actions), actions_per_line):
            chunk = shown_actions[start:start + actions_per_line]
            lines.append(" -> ".join(chunk))

        if len(path) > max_actions:
            lines.append(f"... (+{len(path) - max_actions} actions)")

        return "\n".join(lines)