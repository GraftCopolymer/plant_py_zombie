import abc
from abc import abstractmethod
from typing import Union

import pygame.sprite
from pygame import SurfaceType

from game.character import Position
from base.config import LAYERS

class GameSprite(pygame.sprite.Sprite, abc.ABC):
    """
    游戏精灵
    """
    def __init__(self, group: pygame.sprite.Group, image: SurfaceType, position: Position = pygame.math.Vector2((0,0)), speed: int = 0, z: int = LAYERS['main']):
        pygame.sprite.Sprite.__init__(self, group)
        self.group = group
        self.position = position
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = speed
        self.rect: Union[pygame.Rect, None] = None
        self.image = image
        self.hitbox: Union[pygame.Rect, None] = None
        self.z = z

    @abstractmethod
    def update(self, dt: float) -> None: pass

    def get_z(self):
        return self.z

    def set_position(self, position: Position):
        self.position = position


