from ursina import invoke

class AnimationController:
    def __init__(self, block_view):
        self.block_view = block_view
        self.duration = 0.25 # Khối gỗ sẽ lộn mất 0.25 giây

    def play_move(self, old_state, new_state, on_complete):
        # Đảm bảo truyền cả old_state và new_state vào hàm
        self.block_view.animate_to_state(old_state, new_state, duration=self.duration)
        invoke(on_complete, delay=self.duration)