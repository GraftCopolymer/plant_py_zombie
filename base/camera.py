import pygame.sprite
from pygame import SurfaceType


class CameraGroup(pygame.sprite.Group):
    """
    游戏相机, 用于视角移动和图层管理
    """
    def __init__(self, screen: SurfaceType):
        pygame.sprite.Group.__init__(self)
        self.screen = screen