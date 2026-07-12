from ursina import Entity, Button, Text, color, camera, application

class MenuView:
    def __init__(self, on_start_callback):
        self.root = Entity(parent=camera.ui, name="MenuView")
        self.on_start_callback = on_start_callback
        
        self.title = Text(text="BLOXORZ", parent=self.root, scale=4, position=(-0.25, 0.3), color=color.orange)
        
        # --- Các nút của Main Menu ---
        self.btn_new = Button(text="New Game", parent=self.root, scale=(0.3, 0.08), position=(0, 0.1), color=color.dark_gray, on_click=self.show_slots_for_new)
        self.btn_continue = Button(text="Continue", parent=self.root, scale=(0.3, 0.08), position=(0, 0), color=color.dark_gray, on_click=self.show_slots_for_continue)
        self.btn_quit = Button(text="Quit", parent=self.root, scale=(0.3, 0.08), position=(0, -0.1), color=color.dark_gray, on_click=application.quit)
        
        # --- Các nút Chọn Slot (Ẩn đi lúc đầu) ---
        self.slot_title = Text(text="Select Slot", parent=self.root, scale=2, position=(-0.15, 0.3), color=color.yellow, enabled=False)
        self.btn_slot1 = Button(text="Slot 1", parent=self.root, scale=(0.3, 0.08), position=(0, 0.1), color=color.azure, enabled=False, on_click=lambda: self.select_slot(1))
        self.btn_slot2 = Button(text="Slot 2", parent=self.root, scale=(0.3, 0.08), position=(0, 0), color=color.azure, enabled=False, on_click=lambda: self.select_slot(2))
        self.btn_slot3 = Button(text="Slot 3", parent=self.root, scale=(0.3, 0.08), position=(0, -0.1), color=color.azure, enabled=False, on_click=lambda: self.select_slot(3))
        self.btn_back = Button(text="Back", parent=self.root, scale=(0.3, 0.08), position=(0, -0.2), color=color.red, enabled=False, on_click=self.show_main_menu)
        
        self.is_new_game = True

    def show_slots_for_new(self):
        self.is_new_game = True
        self.toggle_menu(main=False, slots=True)
        self.slot_title.text = "New Game - Override Slot?"

    def show_slots_for_continue(self):
        self.is_new_game = False
        self.toggle_menu(main=False, slots=True)
        self.slot_title.text = "Continue - Select Slot"

    def show_main_menu(self):
        self.toggle_menu(main=True, slots=False)

    def toggle_menu(self, main: bool, slots: bool):
        self.title.enabled = main
        self.btn_new.enabled = main
        self.btn_continue.enabled = main
        self.btn_quit.enabled = main
        
        self.slot_title.enabled = slots
        self.btn_slot1.enabled = slots
        self.btn_slot2.enabled = slots
        self.btn_slot3.enabled = slots
        self.btn_back.enabled = slots

    def select_slot(self, slot: int):
        self.root.enabled = False  # Tắt Menu đi khi đã chọn xong
        self.on_start_callback(slot, self.is_new_game)