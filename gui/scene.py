from ursina import (
    AmbientLight,
    DirectionalLight,
    Entity,
    Vec3,
    camera,
    color
)

from ursina.shaders import lit_with_shadows_shader


class SceneEnvironment:
    """
    Thiết lập môi trường hiển thị chung của game:

    - Màu nền.
    - Mặt đất nhận bóng.
    - Ánh sáng môi trường.
    - Ánh sáng có hướng và bóng đổ.
    """

    def __init__(self) -> None:
        # Nền đỏ nâu, gần phong cách Bloxorz cổ điển.
        camera.background_color = color.rgb32(
            105,
            32,
            22
        )

        # Mặt đất nằm thấp hơn board để nhận bóng đổ.
        self.ground = Entity(
            name="BackgroundGround",
            model="plane",
            texture="white_cube",
            position=(0, -0.65, 0),
            scale=120,
            color=color.rgb32(50, 18, 20),
            shader=lit_with_shadows_shader
        )

        # Ánh sáng môi trường giúp các mặt không bị tối hoàn toàn.
        self.ambient_light = AmbientLight(
            color=color.rgba32(
                125,
                115,
                120,
                255
            )
        )

        # Ánh sáng chính tạo chiều sâu và bóng đổ.
        self.sun_light = DirectionalLight(
            shadows=True
        )

        self.sun_light.color = color.rgb32(
            255,
            220,
            190
        )

        # Hướng chiếu từ trên trái xuống dưới phải.
        self.sun_light.look_at(
            Vec3(1, -2, -1)
        )