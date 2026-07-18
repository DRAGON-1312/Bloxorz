from __future__ import annotations

from pathlib import Path
from random import uniform

from ursina import Audio


class AudioManager:
    """
    Quản lý toàn bộ sound effect của Bloxorz Solver.

    Các View/Controller chỉ gọi play_xxx() và không cần biết:
    - đường dẫn file;
    - volume;
    - pitch;
    - trạng thái Sound On/Off.
    """

    DEFAULT_VOLUMES = {
        "block_move": 0.30,
        "goal_drop": 0.45,
        "victory": 0.45,
        "fall": 0.40,
        "switch": 0.35,
        "bridge": 0.40,
        "ui_click": 0.25,
    }

    def __init__(
        self,
        audio_directory: str | Path | None = None
    ) -> None:
        if audio_directory is None:
            project_root = Path(__file__).resolve().parent.parent
            audio_directory = project_root / "audio"

        self.audio_directory = Path(audio_directory).resolve()
        self.enabled = True

        required_files = {
            name: self.audio_directory / f"{name}.wav"
            for name in self.DEFAULT_VOLUMES
        }

        missing_files = [
            str(path)
            for path in required_files.values()
            if not path.is_file()
        ]

        if missing_files:
            formatted_paths = "\n".join(
                f"- {path}"
                for path in missing_files
            )

            raise FileNotFoundError(
                "Missing required audio files:\n"
                f"{formatted_paths}"
            )

        self.block_move = self._create_audio(
            required_files["block_move"],
            self.DEFAULT_VOLUMES["block_move"]
        )

        self.goal_drop = self._create_audio(
            required_files["goal_drop"],
            self.DEFAULT_VOLUMES["goal_drop"]
        )

        self.victory = self._create_audio(
            required_files["victory"],
            self.DEFAULT_VOLUMES["victory"]
        )

        self.fall = self._create_audio(
            required_files["fall"],
            self.DEFAULT_VOLUMES["fall"]
        )

        self.switch = self._create_audio(
            required_files["switch"],
            self.DEFAULT_VOLUMES["switch"]
        )

        self.bridge = self._create_audio(
            required_files["bridge"],
            self.DEFAULT_VOLUMES["bridge"]
        )

        self.ui_click = self._create_audio(
            required_files["ui_click"],
            self.DEFAULT_VOLUMES["ui_click"]
        )

        self._all_sounds = (
            self.block_move,
            self.goal_drop,
            self.victory,
            self.fall,
            self.switch,
            self.bridge,
            self.ui_click,
        )

    @staticmethod
    def _create_audio(
        path: Path,
        volume: float
    ) -> Audio:
        return Audio(
            path,
            autoplay=False,
            auto_destroy=False,
            loop=False,
            volume=volume
        )

    def set_enabled(
        self,
        is_enabled: bool
    ) -> None:
        self.enabled = bool(is_enabled)

        if not self.enabled:
            self.stop_all()

    def stop_all(self) -> None:
        for sound in self._all_sounds:
            sound.stop(
                destroy=False
            )

    def _play(
        self,
        sound: Audio,
        *,
        vary_pitch: bool = False
    ) -> None:
        if not self.enabled:
            return

        # Các sound effect đều ngắn. Restart từ đầu giúp các lần click
        # hoặc move liên tiếp không bị phát tiếp từ vị trí cũ.
        sound.stop(
            destroy=False
        )

        sound.pitch = (
            uniform(0.97, 1.03)
            if vary_pitch
            else 1.0
        )

        sound.play(
            start=0
        )

    def play_block_move(self) -> None:
        self._play(
            self.block_move,
            vary_pitch=True
        )

    def play_goal_drop(self) -> None:
        self._play(
            self.goal_drop
        )

    def play_victory(self) -> None:
        self._play(
            self.victory
        )

    def play_fall(self) -> None:
        self._play(
            self.fall
        )

    def play_switch(self) -> None:
        self._play(
            self.switch,
            vary_pitch=True
        )

    def play_bridge(self) -> None:
        self._play(
            self.bridge
        )

    def play_ui_click(self) -> None:
        self._play(
            self.ui_click
        )