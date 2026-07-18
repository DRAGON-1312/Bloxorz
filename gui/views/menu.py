from __future__ import annotations

from enum import Enum
from textwrap import fill
from typing import TYPE_CHECKING, Callable

from ursina import Button, Entity, Text, camera, color, window

if TYPE_CHECKING:
    from gui.audio_manager import AudioManager


class MenuScreen(str, Enum):
    """
    Các màn hình con bên trong MenuView.
    """
    MAIN = "main"
    LEVEL_SELECT = "level_select"
    INSTRUCTIONS = "instructions"


class MenuView(Entity):
    """
    Menu chính của Bloxorz Solver trong cùng cửa sổ Ursina.

    Menu gồm:
    - New Game
    - Continue from Stage XX
    - Level Select
    - Resume Current Game
    - Instructions
    - Sound: On / Off
    - Exit

    MenuView chỉ quản lý phần hiển thị và phát callback.
    Việc load level, save game, phát âm thanh và thay đổi Game
    vẫn do BloxorzApp cùng các controller chuyên trách xử lý.
    """

    TITLE_FONT = "VeraMono.ttf"
    BODY_FONT = "VeraMono.ttf"

    # Nếu có texture riêng của block thì đổi ở đây.
    # Nếu chưa có thì giữ "white_cube".
    BLOCK_TEXTURE = "white_cube"

    BACKGROUND_COLOR = color.rgb32(32, 16, 18)
    BACKGROUND_ACCENT = color.rgba32(180, 54, 38, 135)

    PANEL_COLOR = color.rgba32(24, 25, 34, 246)
    PANEL_BORDER_COLOR = color.rgba32(255, 178, 88, 90)

    BUTTON_COLOR = color.rgb32(96, 116, 150)
    BUTTON_HIGHLIGHT = color.rgb32(122, 144, 178)
    BUTTON_PRESSED = color.rgb32(74, 90, 120)
    BUTTON_DISABLED = color.rgb32(108, 108, 116)

    SELECTED_COLOR = color.rgb32(222, 138, 56)

    TITLE_COLOR = color.rgb32(255, 232, 164)
    TITLE_GLOW_COLOR = color.rgba32(255, 156, 62, 100)

    TEXT_COLOR = color.rgb32(244, 246, 250)
    MUTED_TEXT_COLOR = color.rgb32(190, 196, 208)
    WARNING_COLOR = color.rgb32(255, 214, 96)

    # Nội dung Instructions được chia thành nhiều trang,
    # gần với cách hướng dẫn từng bước của Bloxorz gốc.
    INSTRUCTION_PAGES: tuple[tuple[str, str], ...] = (
        (
            "OBJECTIVE",
            (
                "Roll the block across the board and guide it to the "
                "black goal hole.\n\n"
                "To complete a stage, the full block must stand upright "
                "on the goal.\n\n"
                "The block may stand on one tile or lie across two tiles. "
                "A move fails when any occupied part of the block has no "
                "supporting tile."
            )
        ),
        (
            "CONTROLS",
            (
                "W / Up Arrow        Move Up\n"
                "S / Down Arrow      Move Down\n"
                "A / Left Arrow      Move Left\n"
                "D / Right Arrow     Move Right\n\n"
                "Space               Switch active cube in Split Mode\n"
                "R                   Restart the current level\n"
                "N / P               Next / Previous level\n"
                "Esc                 Open or close the menu"
            )
        ),
        (
            "BASIC TILES",
            (
                "WHITE FLOOR\n"
                "Supports the block normally.\n\n"
                "BLACK GOAL\n"
                "The stage is completed only when the full block stands "
                "upright on this hole.\n\n"
                "ORANGE FRAGILE TILE\n"
                "It can support the block while the block is lying down. "
                "If the full block stands upright on it, the tile breaks "
                "and the block falls."
            )
        ),
        (
            "SWITCHES AND BRIDGES",
            (
                "GREEN SOFT SWITCH\n"
                "Activated when any part of the block touches it.\n\n"
                "RED HEAVY SWITCH\n"
                "Activated only when the full block stands upright on it.\n\n"
                "BLUE BRIDGE\n"
                "A switch can open or close its linked bridge tiles. "
                "A closed bridge cannot support the block, so plan the "
                "order of switch activations carefully."
            )
        ),
        (
            "SPLIT MODE",
            (
                "PURPLE SPLIT SWITCH\n"
                "When the full block stands upright on this switch, it "
                "splits into two independent cubes.\n\n"
                "Only one cube is active at a time. Move the active cube "
                "with the normal movement keys and press Space to switch "
                "between the two cubes.\n\n"
                "When the cubes become adjacent in a valid position, they "
                "recombine into the full block. The goal can only be "
                "completed by the recombined block standing upright."
            )
        ),
        (
            "SOLVER AND REPLAY",
            (
                "Open the Solver panel to run BFS, IDS, UCS or A*.\n\n"
                "Each solver searches from the beginning of the current "
                "level and reports search time, peak memory, expanded "
                "nodes, solution length and solution cost.\n\n"
                "Replay restarts the level and performs the solution one "
                "move at a time. Manual controls are locked while replay "
                "is running."
            )
        ),
    )


    def __init__(
        self,
        level_count: int,
        on_new_game: Callable[[], None],
        on_level_selected: Callable[[int], None],
        on_continue: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_sound_changed: Callable[[bool], None] | None = None,
        on_exit: Callable[[], None] | None = None,
        audio_manager: AudioManager | None = None,
        start_visible: bool = True
    ) -> None:
        """
        Khởi tạo MenuView.

        Args:
            level_count:
                Tổng số level hiện có.

            on_new_game:
                Callback khi người dùng bấm New Game.

            on_level_selected:
                Callback nhận index của level được chọn.

            on_continue:
                Callback tải level gần nhất từ save file.

            on_resume:
                Callback đóng menu và quay lại game trong RAM.

            on_sound_changed:
                Callback nhận True/False khi bật hoặc tắt âm thanh.

            on_exit:
                Callback thoát ứng dụng.


            start_visible:
                True để menu xuất hiện ngay khi mở ứng dụng.
        """
        if level_count <= 0:
            raise ValueError(
                "level_count must be greater than 0."
            )

        if not callable(on_new_game):
            raise TypeError(
                "on_new_game must be callable."
            )

        if not callable(on_level_selected):
            raise TypeError(
                "on_level_selected must be callable."
            )

        super().__init__(
            parent=camera.ui,
            name="MenuView"
        )

        # Số level và các callback do BloxorzApp cung cấp.
        self.level_count = level_count
        self.on_new_game = on_new_game
        self.on_continue = on_continue
        self.on_level_selected = on_level_selected
        self.on_resume = on_resume
        self.on_sound_changed = on_sound_changed
        self.on_exit = on_exit
        self.audio_manager = audio_manager

        # Trạng thái của các mục menu.
        self._continue_available = False
        self._continue_level_index: int | None = None
        self._resume_available = False
        self._sound_enabled = True
        self._current_level_index = 0

        # Trang Instructions hiện tại, bắt đầu từ trang đầu tiên.
        self._instruction_page_index = 0

        self.current_screen = MenuScreen.MAIN

        # Mỗi màn hình con giữ danh sách Entity riêng
        # để có thể bật/tắt mà không phá bố cục.
        self._main_items: list[Entity] = []
        self._level_select_items: list[Entity] = []
        self._instructions_items: list[Entity] = []

        # index level -> button tương ứng.
        self.level_buttons: dict[int, Button] = {}

        self._build_background()
        self._build_main_screen()
        self._build_level_select_screen()
        self._build_instructions_screen()

        # Ghi nhớ tỉ lệ cửa sổ hiện tại.
        # update() sẽ dùng giá trị này để phát hiện khi người dùng resize.
        self._last_aspect_ratio = window.aspect_ratio

        # Đồng bộ layout ngay từ lần khởi tạo đầu tiên.
        self._update_responsive_layout(
            self._last_aspect_ratio
        )

        self.show_main_menu()
        self.enabled = start_visible


    @property
    def is_open(self) -> bool:
        """
        True khi menu đang hiển thị.
        """
        return self.enabled


    @property
    def sound_enabled(self) -> bool:
        """
        Trạng thái âm thanh hiện tại của menu.
        """
        return self._sound_enabled
    

    def update(self) -> None:
        """
        Ursina tự động gọi method này ở mỗi frame.

        Chỉ cập nhật lại kích thước nền khi tỉ lệ cửa sổ
        thực sự thay đổi, tránh tính toán thừa ở mọi frame.
        """
        current_aspect_ratio = window.aspect_ratio

        if abs(
            current_aspect_ratio
            - self._last_aspect_ratio
        ) < 0.001:
            return

        self._last_aspect_ratio = (
            current_aspect_ratio
        )

        self._update_responsive_layout(
            current_aspect_ratio
        )


    def _build_background(self) -> None:
        self.background = Entity(
            parent=self,
            name="MenuBackground",
            model="quad",
            texture="white_cube",
            position=(0, 0, 0.10),
            scale=(window.aspect_ratio, 1.0),
            color=self.BACKGROUND_COLOR
        )

        self.background_accent_far = Entity(
            parent=self,
            name="MenuBackgroundAccentFar",
            model="quad",
            texture="white_cube",
            position=(0, 0, 0.095),
            scale=(window.aspect_ratio * 0.98, 0.96),
            color=color.rgba32(108, 30, 22, 100)
        )

        self.background_accent_near = Entity(
            parent=self,
            name="MenuBackgroundAccentNear",
            model="quad",
            texture="white_cube",
            position=(0, 0, 0.09),
            scale=(window.aspect_ratio * 0.94, 0.90),
            color=self.BACKGROUND_ACCENT
        )

        self.panel_glow = Entity(
            parent=self,
            name="MenuPanelGlow",
            model="quad",
            texture="white_cube",
            position=(0, 0, 0.055),
            scale=(0.61, 0.88),
            color=self.PANEL_BORDER_COLOR
        )

        self.panel = Entity(
            parent=self,
            name="MenuPanel",
            model="quad",
            texture="white_cube",
            position=(0, 0, 0.05),
            scale=(0.58, 0.85),
            color=self.PANEL_COLOR
        )


    def _update_responsive_layout(
        self,
        aspect_ratio: float
    ) -> None:
        """
        Cập nhật các lớp nền theo tỉ lệ cửa sổ mới.

        Panel và các thành phần menu vẫn được giữ ở giữa camera.ui.
        """
        self.background.scale = (
            aspect_ratio,
            1.0
        )

        self.background_accent_far.scale = (
            aspect_ratio * 0.98,
            0.96
        )

        self.background_accent_near.scale = (
            aspect_ratio * 0.94,
            0.90
        )


    def _build_main_screen(self) -> None:
        """
        Tạo màn hình Main Menu theo phong cách game hơn:
        - chỉ giữ tên BLOXORZ
        - thêm glow cho title
        - thêm block icon bên phải
        - bỏ subtitle và dòng controls nhỏ ở cuối
        """
        # Title được canh đúng tâm của panel và hạ gần cụm button hơn.
        # Shadow chỉ lệch rất nhẹ để tạo chiều sâu mà không làm chữ bị nhòe.
        title_y = 0.185
        title_scale = 2.85

        self.title_shadow = Text(
            parent=self,
            name="MenuTitleShadow",
            text="BLOXORZ",
            position=(0.006, title_y - 0.008, 0.01),
            origin=(0, 0),
            scale=title_scale,
            color=color.rgba32(105, 48, 27, 225),
            font=self.TITLE_FONT
        )
        self._main_items.append(self.title_shadow)

        self.title_text = Text(
            parent=self,
            name="MenuTitle",
            text="BLOXORZ",
            position=(0, title_y, 0),
            origin=(0, 0),
            scale=title_scale,
            color=self.TITLE_COLOR,
            font=self.TITLE_FONT
        )
        self._main_items.append(self.title_text)

        # Block nhỏ hơn và được đẩy hẳn sang phải để không dính vào title.
        self.logo_block_shadow = Entity(
            parent=self,
            name="MenuLogoBlockShadow",
            model="cube",
            texture=self.BLOCK_TEXTURE,
            position=(0.258, 0.177, -0.035),
            rotation=(12, -28, 8),
            scale=(0.064, 0.112, 0.052),
            color=color.rgba32(255, 145, 58, 38)
        )
        self._main_items.append(self.logo_block_shadow)

        self.logo_block = Entity(
            parent=self,
            name="MenuLogoBlock",
            model="cube",
            texture=self.BLOCK_TEXTURE,
            position=(0.250, 0.186, -0.02),
            rotation=(12, -28, 8),
            scale=(0.058, 0.103, 0.046),
            color=color.rgb32(198, 132, 94)
        )
        self._main_items.append(self.logo_block)

        button_data = [
            ("NewGameButton", "New Game", 0.060, self._request_new_game),
            ("ContinueButton", "Continue", -0.008, self._request_continue),
            ("LevelSelectButton", "Level Select", -0.076, self.show_level_select),
            ("ResumeButton", "Resume Game", -0.144, self._request_resume),
            ("InstructionsButton", "Instructions", -0.212, self.show_instructions),
            ("SoundButton", "Sound: On", -0.280, self._request_toggle_sound),
            ("ExitButton", "Exit", -0.348, self._request_exit),
        ]

        created_buttons: dict[str, Button] = {}

        for name, text, y, callback in button_data:
            created_buttons[name] = self._create_main_button(
                name=name,
                text=text,
                y=y,
                callback=callback
            )

        self.new_game_button = created_buttons["NewGameButton"]
        self.continue_button = created_buttons["ContinueButton"]
        self.level_select_button = created_buttons["LevelSelectButton"]
        self.resume_button = created_buttons["ResumeButton"]
        self.instructions_button = created_buttons["InstructionsButton"]
        self.sound_button = created_buttons["SoundButton"]
        self.exit_button = created_buttons["ExitButton"]

        self.status_text = Text(
            parent=self,
            name="MenuStatusText",
            text="",
            position=(0, -0.418, 0),
            origin=(0, 0),
            scale=0.62,
            color=self.WARNING_COLOR,
            font=self.BODY_FONT
        )
        self._main_items.append(self.status_text)

        self._refresh_main_button_states()


    def _build_level_select_screen(self) -> None:
        """
        Tạo màn hình chọn level.
        """
        title = Text(
            parent=self,
            name="LevelSelectTitle",
            text="SELECT LEVEL",
            position=(0, 0.38, 0),
            origin=(0, 0),
            scale=1.35,
            color=self.TITLE_COLOR
        )
        self._level_select_items.append(title)

        description = Text(
            parent=self,
            name="LevelSelectDescription",
            text="Choose a stage to play or test the solvers.",
            position=(0, 0.31, 0),
            origin=(0, 0),
            scale=0.68,
            color=self.MUTED_TEXT_COLOR
        )
        self._level_select_items.append(description)

        columns = min(5, self.level_count)
        button_width = 0.085
        horizontal_gap = 0.105
        vertical_gap = 0.095

        for index in range(self.level_count):
            row = index // columns
            col = index % columns

            items_in_row = min(
                columns,
                self.level_count - row * columns
            )

            row_width = (
                (items_in_row - 1) * horizontal_gap
            )

            start_x = -row_width / 2
            x_position = start_x + col * horizontal_gap
            y_position = 0.16 - row * vertical_gap

            button = Button(
                parent=self,
                name=f"LevelButton{index + 1}",
                text=f"{index + 1:02d}",
                position=(
                    x_position,
                    y_position,
                    0
                ),
                scale=(
                    button_width,
                    0.060
                ),
                color=self.BUTTON_COLOR,
                highlight_color=self.BUTTON_HIGHLIGHT,
                pressed_color=self.BUTTON_PRESSED,
                text_color=color.white,
                on_click=self._with_click(
                    lambda selected_index=index:
                    self._request_level(selected_index)
                )
            )

            self.level_buttons[index] = button
            self._level_select_items.append(button)

        self.level_hint_text = Text(
            parent=self,
            name="LevelHintText",
            text="Selected: Stage 01",
            position=(0, -0.16, 0),
            origin=(0, 0),
            scale=0.70,
            color=self.TEXT_COLOR
        )
        self._level_select_items.append(
            self.level_hint_text
        )

        self.level_back_button = self._create_back_button(
            parent_items=self._level_select_items,
            name="LevelSelectBackButton"
        )

        self._refresh_level_buttons()


    def _build_instructions_screen(self) -> None:
        """
        Tạo Instructions dạng nhiều trang.

        Mỗi trang tập trung vào một nhóm luật chơi để nội dung dễ đọc,
        tương tự cách Bloxorz gốc hướng dẫn từng cơ chế theo từng bước.
        """
        self.instructions_title = Text(
            parent=self,
            name="InstructionsTitle",
            text="INSTRUCTIONS",
            position=(0, 0.38, 0),
            origin=(0, 0),
            scale=1.30,
            color=self.TITLE_COLOR,
            font=self.TITLE_FONT
        )
        self._instructions_items.append(
            self.instructions_title
        )

        self.instructions_page_indicator = Text(
            parent=self,
            name="InstructionsPageIndicator",
            text="1 / 6",
            position=(-0.235, 0.315, 0),
            origin=(-0.5, 0),
            scale=0.62,
            color=self.MUTED_TEXT_COLOR,
            font=self.BODY_FONT
        )
        self._instructions_items.append(
            self.instructions_page_indicator
        )

        self.instructions_section_title = Text(
            parent=self,
            name="InstructionsSectionTitle",
            text="OBJECTIVE",
            position=(-0.235, 0.250, 0),
            origin=(-0.5, 0),
            scale=0.82,
            color=self.TITLE_COLOR,
            font=self.BODY_FONT
        )
        self._instructions_items.append(
            self.instructions_section_title
        )

        self.instructions_body = Text(
            parent=self,
            name="InstructionsBody",
            text="",
            position=(-0.235, 0.185, 0),
            origin=(-0.5, 0.5),
            scale=0.61,
            color=self.TEXT_COLOR,
            font=self.BODY_FONT
        )

        self._instructions_items.append(
            self.instructions_body
        )

        self.instructions_previous_button = (
            self._create_instruction_navigation_button(
                name="InstructionsPreviousButton",
                text="< Previous",
                x=-0.175,
                callback=self._show_previous_instruction_page
            )
        )

        self.instructions_back_button = (
            self._create_instruction_navigation_button(
                name="InstructionsBackButton",
                text="Back to Menu",
                x=0,
                callback=self.show_main_menu
            )
        )

        self.instructions_next_button = (
            self._create_instruction_navigation_button(
                name="InstructionsNextButton",
                text="Next >",
                x=0.175,
                callback=self._show_next_instruction_page
            )
        )

        self._refresh_instruction_page()



    def _create_main_button(
        self,
        name: str,
        text: str,
        y: float,
        callback: Callable[[], None]
    ) -> Button:
        """
        Tạo button chính và một label độc lập luôn nằm phía trước button.

        Không dùng Text nội bộ của Button vì label đó có thể bị z-fighting
        và chỉ hiện rõ sau khi hover trên một số cấu hình Ursina/Panda3D.
        """
        button = Button(
            parent=self,
            name=name,
            text="",
            position=(0, y, 0),
            scale=(0.41, 0.062),
            color=self.BUTTON_COLOR,
            highlight_color=self.BUTTON_HIGHLIGHT,
            pressed_color=self.BUTTON_PRESSED,
            on_click=self._with_click(callback)
        )

        # Label là sibling của Button, không bị scale méo theo button
        # và luôn được đặt gần camera hơn bằng z âm.
        label = Text(
            parent=self,
            name=f"{name}Label",
            text=text,
            position=(0, y, -0.02),
            origin=(0, 0),
            scale=0.88,
            color=self.TEXT_COLOR,
            font=self.BODY_FONT
        )

        # Lưu label trong button để các method refresh cập nhật trực tiếp.
        button.menu_label = label

        self._main_items.append(button)
        self._main_items.append(label)
        return button


    def _create_instruction_navigation_button(
        self,
        name: str,
        text: str,
        x: float,
        callback: Callable[[], None]
    ) -> Button:
        """
        Tạo nút điều hướng Instructions với label độc lập,
        tránh lỗi chữ chỉ hiện rõ sau khi hover.
        """
        y_position = -0.360

        button = Button(
            parent=self,
            name=name,
            text="",
            position=(x, y_position, 0),
            scale=(0.145, 0.056),
            color=self.BUTTON_COLOR,
            highlight_color=self.BUTTON_HIGHLIGHT,
            pressed_color=self.BUTTON_PRESSED,
            on_click=self._with_click(callback)
        )

        label = Text(
            parent=self,
            name=f"{name}Label",
            text=text,
            position=(x, y_position, -0.02),
            origin=(0, 0),
            scale=0.58,
            color=self.TEXT_COLOR,
            font=self.BODY_FONT
        )

        button.menu_label = label

        self._instructions_items.append(button)
        self._instructions_items.append(label)

        return button



    def _create_back_button(
        self,
        parent_items: list[Entity],
        name: str
    ) -> Button:
        """
        Tạo nút Back dùng chung cho các màn hình con.
        """
        button = Button(
            parent=self,
            name=name,
            text="Back",
            position=(0, -0.36, 0),
            scale=(0.22, 0.058),
            color=self.BUTTON_COLOR,
            highlight_color=self.BUTTON_HIGHLIGHT,
            pressed_color=self.BUTTON_PRESSED,
            text_color=color.white,
            on_click=self._with_click(
                self.show_main_menu
            )
        )

        parent_items.append(button)
        return button


    def show(self) -> None:
        """
        Hiện menu tại Main Menu và đồng bộ lại kích thước
        trong trường hợp cửa sổ đã được resize khi menu đang ẩn.
        """
        current_aspect_ratio = window.aspect_ratio

        self._last_aspect_ratio = (
            current_aspect_ratio
        )

        self._update_responsive_layout(
            current_aspect_ratio
        )

        self.enabled = True
        self.show_main_menu()


    def hide(self) -> None:
        """
        Ẩn toàn bộ menu.
        """
        self.enabled = False


    def show_main_menu(self) -> None:
        self.current_screen = MenuScreen.MAIN
        self.status_text.text = ""

        self._show_only(
            self._main_items
        )

        self._refresh_main_button_states()


    def show_level_select(self) -> None:
        self.current_screen = MenuScreen.LEVEL_SELECT

        self._show_only(
            self._level_select_items
        )

        self._refresh_level_buttons()


    def show_instructions(self) -> None:
        self.current_screen = MenuScreen.INSTRUCTIONS

        # Mỗi lần mở Instructions đều bắt đầu từ phần mục tiêu.
        self._instruction_page_index = 0
        self._refresh_instruction_page()

        self._show_only(
            self._instructions_items
        )



    def _show_previous_instruction_page(self) -> None:
        """
        Chuyển sang trang Instructions trước đó.
        """
        if self._instruction_page_index <= 0:
            return

        self._instruction_page_index -= 1
        self._refresh_instruction_page()


    def _show_next_instruction_page(self) -> None:
        """
        Chuyển sang trang Instructions tiếp theo.
        """
        last_page_index = (
            len(self.INSTRUCTION_PAGES) - 1
        )

        if self._instruction_page_index >= last_page_index:
            return

        self._instruction_page_index += 1
        self._refresh_instruction_page()


    @staticmethod
    def _wrap_instruction_text(
        text: str,
        width: int = 45
    ) -> str:
        """
        Tự xuống dòng bằng thư viện chuẩn Python.

        Không dùng Text.wordwrap của Ursina vì setter đó gây lỗi
        raw_text trong phiên bản Ursina đang chạy trên máy hiện tại.

        Hàm giữ nguyên các dòng trống và các dòng điều khiển đã căn sẵn.
        """
        wrapped_lines: list[str] = []

        for line in text.splitlines():
            if not line:
                wrapped_lines.append("")
                continue

            wrapped_lines.append(
                fill(
                    line,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                    replace_whitespace=False,
                    drop_whitespace=True
                )
            )

        return "\n".join(wrapped_lines)


    def _refresh_instruction_page(self) -> None:
        """
        Hiển thị nội dung và trạng thái nút của trang Instructions hiện tại.
        """
        page_title, page_body = self.INSTRUCTION_PAGES[
            self._instruction_page_index
        ]

        total_pages = len(
            self.INSTRUCTION_PAGES
        )

        self.instructions_page_indicator.text = (
            f"{self._instruction_page_index + 1} / {total_pages}"
        )

        self.instructions_section_title.text = (
            page_title
        )

        self.instructions_body.text = (
            self._wrap_instruction_text(
                page_body,
                width=45
            )
        )

        is_first_page = (
            self._instruction_page_index == 0
        )

        is_last_page = (
            self._instruction_page_index
            == total_pages - 1
        )

        self.instructions_previous_button.color = (
            self.BUTTON_DISABLED
            if is_first_page
            else self.BUTTON_COLOR
        )

        self.instructions_previous_button.menu_label.color = (
            self.MUTED_TEXT_COLOR
            if is_first_page
            else self.TEXT_COLOR
        )

        self.instructions_next_button.color = (
            self.BUTTON_DISABLED
            if is_last_page
            else self.BUTTON_COLOR
        )

        self.instructions_next_button.menu_label.color = (
            self.MUTED_TEXT_COLOR
            if is_last_page
            else self.TEXT_COLOR
        )



    def handle_escape(self) -> bool:
        """
        Xử lý phím Escape.

        - Ở màn hình con: quay về Main Menu.
        - Ở Main Menu khi đang có game: Resume.
        """
        if not self.is_open:
            return False

        if self.current_screen != MenuScreen.MAIN:
            self.show_main_menu()
            return True

        if self._resume_available:
            self._request_resume()
            return True

        return True


    def set_continue_available(
        self,
        is_available: bool
    ) -> None:
        self._continue_available = bool(
            is_available
        )
        self._refresh_main_button_states()


    def set_continue_level(
        self,
        level_index: int | None
    ) -> None:
        """
        Cập nhật Stage hiển thị trong nút Continue.

        level_index=None nghĩa là chưa biết hoặc chưa có save.
        """
        if level_index is not None:
            if not 0 <= level_index < self.level_count:
                raise IndexError(
                    f"Invalid continue level index: {level_index}."
                )

        self._continue_level_index = level_index
        self._refresh_main_button_states()


    def set_resume_available(
        self,
        is_available: bool
    ) -> None:
        self._resume_available = bool(
            is_available
        )
        self._refresh_main_button_states()


    def set_sound_enabled(
        self,
        is_enabled: bool
    ) -> None:
        self._sound_enabled = bool(
            is_enabled
        )
        self._refresh_main_button_states()


    def set_current_level(
        self,
        level_index: int
    ) -> None:
        """
        Cập nhật level đang chơi và highlight button tương ứng.
        """
        if not 0 <= level_index < self.level_count:
            raise IndexError(
                f"Invalid level index: {level_index}."
            )

        self._current_level_index = level_index
        self._refresh_level_buttons()



    def _request_new_game(self) -> None:
        self.status_text.text = ""
        self.on_new_game()


    def _request_continue(self) -> None:
        if (
            not self._continue_available
            or self.on_continue is None
        ):
            self.status_text.text = (
                "No saved game was found."
            )
            return

        self.status_text.text = ""
        self.on_continue()


    def _request_resume(self) -> None:
        if (
            not self._resume_available
            or self.on_resume is None
        ):
            self.status_text.text = (
                "Start a game before using Resume."
            )
            return

        self.status_text.text = ""
        self.on_resume()


    def _request_toggle_sound(self) -> None:
        """
        Đổi trạng thái âm thanh và thông báo cho BloxorzApp.
        """
        self._sound_enabled = not self._sound_enabled
        self._refresh_main_button_states()

        if self.on_sound_changed is not None:
            self.on_sound_changed(
                self._sound_enabled
            )

        # Khi bật từ Off -> On, click wrapper đã chạy lúc AudioManager
        # còn bị tắt. Phát lại một click sau khi callback bật âm thanh.
        if self._sound_enabled:
            self._play_ui_click()


    def _request_exit(self) -> None:
        if self.on_exit is not None:
            self.on_exit()


    def _request_level(
        self,
        level_index: int
    ) -> None:
        self.set_current_level(
            level_index
        )

        self.on_level_selected(
            level_index
        )



    def _play_ui_click(self) -> None:
        if self.audio_manager is not None:
            self.audio_manager.play_ui_click()


    def _with_click(
        self,
        callback: Callable
    ) -> Callable:
        def wrapped_callback(*args, **kwargs):
            self._play_ui_click()
            return callback(*args, **kwargs)

        return wrapped_callback


    @staticmethod
    def _set_button_label(
        button: Button,
        text: str
    ) -> None:
        """
        Cập nhật label độc lập của button.
        """
        button.menu_label.text = text
        button.menu_label.enabled = True


    def _set_button_text_style(
        self,
        button: Button,
        *,
        is_enabled: bool
    ) -> None:
        """
        Giữ label luôn hiển thị và dễ đọc, kể cả khi button bị disable.
        """
        button.menu_label.enabled = True

        if is_enabled:
            button.menu_label.color = self.TEXT_COLOR
        else:
            button.menu_label.color = color.rgb32(226, 230, 238)


    def _refresh_main_button_states(self) -> None:
        """
        Cập nhật text và màu của Continue, Resume và Sound.
        """
        if self._continue_available:
            if self._continue_level_index is None:
                self._set_button_label(self.continue_button, "Continue")
            else:
                self._set_button_label(
                    self.continue_button,
                    f"Continue - Stage {self._continue_level_index + 1:02d}"
                )

            self.continue_button.color = self.BUTTON_COLOR
            self._set_button_text_style(
                self.continue_button,
                is_enabled=True
            )

        else:
            self._set_button_label(self.continue_button, "Continue")
            self.continue_button.color = self.BUTTON_DISABLED
            self._set_button_text_style(
                self.continue_button,
                is_enabled=False
            )

        self._set_button_label(self.resume_button, "Resume Game")

        if self._resume_available:
            self.resume_button.color = self.BUTTON_COLOR
            self._set_button_text_style(
                self.resume_button,
                is_enabled=True
            )
        else:
            self.resume_button.color = self.BUTTON_DISABLED
            self._set_button_text_style(
                self.resume_button,
                is_enabled=False
            )

        self._set_button_label(
            self.sound_button,
            "Sound: On"
            if self._sound_enabled
            else "Sound: Off"
        )
        self.sound_button.color = self.BUTTON_COLOR
        self._set_button_text_style(
            self.sound_button,
            is_enabled=True
        )

        self.new_game_button.color = self.BUTTON_COLOR
        self.level_select_button.color = self.BUTTON_COLOR
        self.instructions_button.color = self.BUTTON_COLOR
        self.exit_button.color = self.BUTTON_COLOR

        self._set_button_text_style(self.new_game_button, is_enabled=True)
        self._set_button_text_style(self.level_select_button, is_enabled=True)
        self._set_button_text_style(self.instructions_button, is_enabled=True)
        self._set_button_text_style(self.exit_button, is_enabled=True)


    def _refresh_level_buttons(self) -> None:
        for index, button in self.level_buttons.items():
            button.color = (
                self.SELECTED_COLOR
                if index == self._current_level_index
                else self.BUTTON_COLOR
            )

        if hasattr(self, "level_hint_text"):
            self.level_hint_text.text = (
                "Selected: "
                f"Stage {self._current_level_index + 1:02d}"
            )


    def _show_only(
        self,
        visible_items: list[Entity]
    ) -> None:
        """
        Chỉ hiện một nhóm Entity thuộc màn hình được chọn.
        """
        item_groups = [
            self._main_items,
            self._level_select_items,
            self._instructions_items,
        ]

        for items in item_groups:
            self._set_items_enabled(
                items,
                items is visible_items
            )


    @staticmethod
    def _set_items_enabled(
        items: list[Entity],
        is_enabled: bool
    ) -> None:
        """
        Bật hoặc tắt toàn bộ Entity trong một nhóm.
        """
        for item in items:
            item.enabled = is_enabled