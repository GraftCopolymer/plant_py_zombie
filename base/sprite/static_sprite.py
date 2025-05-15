from typing import Union

import pygame.time
from pygame import Surface

from base.sprite.game_sprite import GameSprite
from game.character import Position


class StaticSprite(GameSprite):
    """
    静态精灵，无动画，仅显示一个图片或色块，但仍可以移动
    """



    def __init__(self, group: Union[pygame.sprite.Group, list], image: Surface, position: Position):
        GameSprite.__init__(self, group, image, position)
        self.image = image
        self.world_pos = position
        self.rect = self.image.get_rect()

    def update(self, dt: float) -> None:
        GameSprite.update(self, dt)

    def setup_sprite(self, *args, **kwargs) -> None:
        super().setup_sprite(*args, **kwargs)
