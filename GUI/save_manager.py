import json
import os
from pathlib import Path

class SaveManager:
    def __init__(self, save_dir="saves"):
        self.save_dir = save_dir
        # Tự động tạo thư mục saves nếu chưa có
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def get_save_path(self, slot: int) -> str:
        return os.path.join(self.save_dir, f"slot_{slot}.json")

    def load_save(self, slot: int) -> int:
        path = self.get_save_path(slot)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get("level_index", 0)
        return 0  # Trả về level 0 nếu slot này trống (chưa từng chơi)

    def save_game(self, slot: int, level_index: int):
        path = self.get_save_path(slot)
        with open(path, 'w') as f:
            json.dump({"level_index": level_index}, f)