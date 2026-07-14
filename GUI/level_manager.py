from pathlib import Path

from core.level_loader import load_level
from core.board import Board


class LevelManager:
    def __init__(self, levels_dir: str = "levels"):
        self.levels_dir = Path(levels_dir)
        self.level_paths: list[Path] = []
        self.current_index: int = 0

        self.discover_levels()

    def discover_levels(self) -> list[Path]:
        self.level_paths = sorted(
    self.levels_dir.rglob("*.json"),
    key=lambda path: path.stem
)

        if not self.level_paths:
            raise FileNotFoundError(
                f"No .json level file found in: {self.levels_dir}"
            )

        return self.level_paths

    def get_level_count(self) -> int:
        return len(self.level_paths)

    def get_current_path(self) -> Path:
        return self.level_paths[self.current_index]

    def get_current_name(self) -> str:
        return self.get_current_path().stem

    def load_current_level(self) -> Board:
        return load_level(str(self.get_current_path()))

    def load_level_by_index(self, index: int) -> Board:
        if index < 0 or index >= len(self.level_paths):
            raise IndexError(
                f"Invalid level index: {index}. "
                f"There currently are {len(self.level_paths)} levels."
            )

        self.current_index = index
        return self.load_current_level()

    def load_level_by_path(self, level_path: str | Path) -> Board:
        path = Path(level_path)

        if not path.exists():
            raise FileNotFoundError(f"Could not find level: {path}")

        self.level_paths = sorted(set(self.level_paths + [path]))
        self.current_index = self.level_paths.index(path)

        return load_level(str(path))

    def next_level(self) -> Board:
        self.current_index = (self.current_index + 1) % len(self.level_paths)
        return self.load_current_level()

    def previous_level(self) -> Board:
        self.current_index = (self.current_index - 1) % len(self.level_paths)
        return self.load_current_level()

    def restart_level(self) -> Board:
        return self.load_current_level()