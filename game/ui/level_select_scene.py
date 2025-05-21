from pygame import Surface

from base.scene import AbstractScene


class LevelSelectScene(AbstractScene):
    """
    关卡选择页面，将列出所有可用关卡
    """
    def __init__(self):
        super().__init__(name='level_select_scene')

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        pass

    def setup_ui(self, *args, **kwargs) -> None:
        pass