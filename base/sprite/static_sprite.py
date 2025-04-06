import pygame.time
from pygame import SurfaceType

from base.sprite.game_sprite import GameSprite
from game.character import Position


class StaticSprite(GameSprite):
    def __init__(self, group: pygame.sprite.Group, image: SurfaceType, position: Position):
        GameSprite.__init__(self, group, position)
        self.image = image
        self.position = position
        self.rect = self.image.get_rect()

    def update(self, dt: float) -> None:
        GameSprite.update(self, dt)
