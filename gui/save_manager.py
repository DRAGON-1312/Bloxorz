from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SaveManager:
    """
    Quản lý file save của Bloxorz Solver.

    Phiên bản hiện tại chỉ lưu level gần nhất mà người chơi đã mở:

        {
            "version": 1,
            "level_index": 4
        }

    Vì vậy, chức năng Continue sẽ mở lại Stage 05 từ đầu,
    không khôi phục chính xác vị trí block, bridge hoặc move count.

    SaveManager không:
    - Tự load Board.
    - Tự thay đổi GameController.
    - Tự cập nhật MenuView.

    Những việc đó thuộc BloxorzApp.
    """

    SAVE_VERSION = 1


    def __init__(
        self,
        save_dir: str | Path | None = None
    ) -> None:
        """
        Khởi tạo SaveManager.

        Args:
            save_dir:
                Thư mục chứa file save.

                Nếu không truyền vào, thư mục mặc định là:

                    <project_root>/saves

                Trong đó project_root là thư mục chứa gui/.
        """
        if save_dir is None:
            # File này nằm tại:
            #     project_root/gui/save_manager.py
            #
            # parent        -> gui
            # parent.parent -> project_root
            project_root = (
                Path(__file__).resolve().parent.parent
            )

            self.save_dir = (
                project_root / "saves"
            )
        else:
            self.save_dir = Path(
                save_dir
            ).expanduser().resolve()

        # Tạo thư mục saves nếu chưa tồn tại.
        self.save_dir.mkdir(
            parents=True,
            exist_ok=True
        )


    def get_save_path(
        self,
        slot: int
    ) -> Path:
        """
        Trả về đường dẫn file của một save slot.

        Ví dụ:
            slot = 1
            -> saves/slot_1.json
        """
        self._validate_slot(slot)

        return (
            self.save_dir
            / f"slot_{slot}.json"
        )


    def has_save(
        self,
        slot: int
    ) -> bool:
        """
        True khi slot tồn tại và chứa dữ liệu hợp lệ.

        File bị hỏng hoặc sai cấu trúc không được xem là save hợp lệ.
        """
        return self.load_save(slot) is not None


    def load_save(
        self,
        slot: int
    ) -> int | None:
        """
        Đọc level_index từ save slot.

        Return:
            int:
                Index của level đã lưu.

            None:
                Slot chưa tồn tại, file bị hỏng hoặc dữ liệu không hợp lệ.

        Hàm không tự load level. BloxorzApp sẽ dùng level_index trả về
        để gọi LevelManager.load_by_index().
        """
        save_path = self.get_save_path(
            slot
        )

        if not save_path.exists():
            return None

        try:
            with save_path.open(
                mode="r",
                encoding="utf-8"
            ) as save_file:
                data: Any = json.load(
                    save_file
                )

        except (
            OSError,
            json.JSONDecodeError
        ):
            # Không làm crash game khi file bị hỏng hoặc không đọc được.
            return None

        if not isinstance(data, dict):
            return None

        # Những file save cũ chưa có version vẫn được xem là version 1.
        version = data.get(
            "version",
            self.SAVE_VERSION
        )

        level_index = data.get(
            "level_index"
        )

        if (
            not isinstance(version, int)
            or isinstance(version, bool)
            or version != self.SAVE_VERSION
        ):
            return None

        if (
            not isinstance(level_index, int)
            or isinstance(level_index, bool)
            or level_index < 0
        ):
            return None

        return level_index


    def save_game(
        self,
        slot: int,
        level_index: int
    ) -> None:
        """
        Lưu level gần nhất vào save slot.

        File được ghi qua một file tạm rồi mới replace file chính.
        Cách này hạn chế trường hợp file save bị ghi dở nếu chương trình
        bị đóng giữa lúc đang lưu.
        """
        self._validate_slot(slot)
        self._validate_level_index(
            level_index
        )

        save_path = self.get_save_path(
            slot
        )

        temporary_path = (
            save_path.with_suffix(".tmp")
        )

        save_data = {
            "version": self.SAVE_VERSION,
            "level_index": level_index,
        }

        try:
            with temporary_path.open(
                mode="w",
                encoding="utf-8"
            ) as save_file:
                json.dump(
                    save_data,
                    save_file,
                    ensure_ascii=False,
                    indent=4
                )

                # Ghi ký tự xuống dòng ở cuối file để JSON dễ đọc hơn.
                save_file.write("\n")

            # Thay file save cũ bằng file tạm vừa ghi hoàn chỉnh.
            temporary_path.replace(
                save_path
            )

        except OSError:
            # Dọn file tạm nếu quá trình ghi thất bại.
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            raise


    def delete_save(
        self,
        slot: int
    ) -> bool:
        """
        Xóa một save slot.

        Return:
            True:
                File save đã tồn tại và được xóa.

            False:
                Slot chưa có file save.
        """
        save_path = self.get_save_path(
            slot
        )

        if not save_path.exists():
            return False

        save_path.unlink()
        return True


    @staticmethod
    def _validate_slot(
        slot: int
    ) -> None:
        """
        Save slot phải là số nguyên dương: 1, 2, 3, ...
        """
        if (
            not isinstance(slot, int)
            or isinstance(slot, bool)
            or slot <= 0
        ):
            raise ValueError(
                "Save slot must be a positive integer."
            )


    @staticmethod
    def _validate_level_index(
        level_index: int
    ) -> None:
        """
        Level index phải là số nguyên không âm.
        """
        if (
            not isinstance(level_index, int)
            or isinstance(level_index, bool)
            or level_index < 0
        ):
            raise ValueError(
                "level_index must be a non-negative integer."
            )