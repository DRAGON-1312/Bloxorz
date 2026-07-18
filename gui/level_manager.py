import re
from pathlib import Path

from core.board import Board
from core.level_loader import load_level


class LevelManager:
    """
    Quản lý danh sách level và level đang được chọn.

    Trách nhiệm chính:
    - Tìm tất cả file stage_*.json trong thư mục levels.
    - Sắp xếp các level theo số thứ tự: stage_01, stage_02, ...
    - Load level hiện tại.
    - Chuyển sang level kế tiếp hoặc trước đó.
    """

    def __init__(
        self,
        levels_dir: str | Path | None = None
    ):
        """
        Khởi tạo LevelManager.

        Nếu không truyền levels_dir, chương trình tự xác định thư mục
        levels nằm ở thư mục gốc của project, ngang hàng với thư mục gui.
        """
        if levels_dir is None:
            # parent       -> gui
            # parent.parent -> project_root
            project_root = Path(__file__).resolve().parent.parent
            self.levels_dir = project_root / "levels"
        else:
            # Cho phép truyền thư mục riêng khi testing.
            self.levels_dir = Path(levels_dir).resolve()

        self.level_paths: list[Path] = self._discover_levels()
        self.current_index: int = 0


    @staticmethod
    def _get_stage_number(path: Path) -> int:
        """
        Lấy số thứ tự stage từ tên file.

        Ví dụ:
            stage_01.json -> 1
            stage_09.json -> 9
            stage_10.json -> 10

        Nếu tên file không đúng định dạng stage_<number>,
        trả về một số rất lớn để file đó bị đẩy xuống cuối danh sách.
        """
        # path.stem lấy tên file mà không có phần mở rộng.
        # Path("stage_09.json").stem -> "stage_09"
        file_name = path.stem.lower()

        # Tìm mẫu:
        # stage_ + một hoặc nhiều chữ số
        # \d+ nghĩa là một hoặc nhiều chữ số.
        match = re.search(r"stage_(\d+)", file_name)

        # Nếu tên file không chứa dạng stage_<number>.
        if match is None:
            # Đẩy file không đúng định dạng xuống cuối khi sort.
            return 10**9

        # match.group(1) lấy phần số nằm trong cặp ngoặc (\d+).
        # Ví dụ:
        # "stage_09" -> group(1) là "09"
        # int("09") -> 9
        return int(match.group(1))
    

    def _discover_levels(self) -> list[Path]:
        """
        Tìm và sắp xếp tất cả file level.

        Chỉ tìm những file có tên phù hợp với:
            stage_*.json

        Việc tìm kiếm được thực hiện trong levels_dir và toàn bộ
        các thư mục con của nó.
        """
        # rglob() tìm file trong thư mục hiện tại và tất cả thư mục con.
        paths = list(self.levels_dir.rglob("stage_*.json"))

        # Sắp xếp level trước hết theo số stage.
        paths.sort(
            key=lambda path: (
                self._get_stage_number(path),
                str(path)
            )
        )

        # Nếu không tìm được file level nào thì báo lỗi ngay,
        # tránh để chương trình tiếp tục rồi lỗi khó hiểu ở chỗ khác.
        if not paths:
            raise FileNotFoundError(
                f"No stage JSON files found in '{self.levels_dir}'."
            )

        return paths


    def get_level_count(self) -> int:
        return len(self.level_paths)
    


    def is_last_level(self) -> bool:
        """
        True khi current_index đang ở level cuối.
        """
        return (
            self.current_index
            == len(self.level_paths) - 1
        )


    def has_next_level(self) -> bool:
        """
        True khi còn level kế tiếp.
        """
        return (
            self.current_index
            < len(self.level_paths) - 1
        )


    def load_current(self) -> Board:
        """
        Load level đang được chọn bởi current_index.
        Hàm trả về một đối tượng Board.
        """
        # Get current path
        current_path = self.level_paths[self.current_index]

        # load_level() hiện nhận đường dẫn dạng str,
        # nên chuyển Path thành chuỗi trước khi truyền vào.
        return load_level(str(current_path))
    

    def load_by_index(self, index: int) -> Board:
        """
        Chọn và load một level theo index.

        Lưu ý:
        - index = 0 tương ứng Stage 01
        - index = 1 tương ứng Stage 02
        - ...
        """
        if not 0 <= index < len(self.level_paths):
            raise IndexError(f"Invalid level index: {index}")
        
        self.current_index = index

        # load level 
        return self.load_current()
    

    def next_level(self) -> Board:
        """
        Chuyển sang level kế tiếp và load level đó.

        Không quay vòng về Stage 01 khi đang ở level cuối.
        """
        if not self.has_next_level():
            raise IndexError(
                "Current level is already the final level."
            )

        self.current_index += 1

        return self.load_current()
    

    def previous_level(self) -> Board:
        """
        Chuyển về level trước đó và load level đó.

        Nhờ toán tử %, nếu đang ở Stage 01 thì sẽ quay về level cuối.
        """
        self.current_index = (
            self.current_index - 1
        ) % len(self.level_paths)

        return self.load_current()
    

if __name__ == "__main__":
    manager = LevelManager()

    print("Levels directory:", manager.levels_dir)
    print("Level count:", manager.get_level_count())

    for index, path in enumerate(manager.level_paths):
        print(index, path.name)

    board = manager.load_current()
    print("Current level:", board.name)