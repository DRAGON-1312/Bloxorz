from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.state import State


class MoveStatus(Enum):
    """
    Kết quả của một action trong chế độ chơi thủ công.
    """

    IGNORED = "ignored"
    MOVED = "moved"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class MoveResult:
    """
    Kết quả chi tiết của một action.

    previous_state:
        State trước khi action được thực hiện.

    attempted_state:
        State mà block đã cố di chuyển đến.
        GUI dùng state này để phát animation rơi khi LOST.

    resulting_state:
        State hợp lệ cuối cùng sau action.
        Chỉ có khi MOVED hoặc WON.

    reason:
        Lý do action bị bỏ qua hoặc dẫn đến thua.
    """

    status: MoveStatus
    previous_state: State
    attempted_state: State | None = None
    resulting_state: State | None = None
    reason: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status in {
            MoveStatus.MOVED,
            MoveStatus.WON,
        }

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            MoveStatus.WON,
            MoveStatus.LOST,
        }