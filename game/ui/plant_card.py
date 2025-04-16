from typing import Union, Optional, TypeVar, Type

import pygame.transform
from pygame import Surface, Vector2
from pygame.sprite import Group

from base.sprite.game_sprite import GameSprite
from game.character.plant import AbstractPlant

PlantT = TypeVar("PlantT", bound=AbstractPlant)

class PlantCard(GameSprite):
    def __init__(self, group: Union[Group, list], plant_cls: Type[PlantT], image: Surface, position: Vector2 = Vector2(0, 0)):
        super().__init__(group, image, position)
        self.scale = 0.75
        self.image = image
        self.image = pygame.transform.scale(self.image, (self.image.width * self.scale, self.image.height * self.scale))
        self.rect = self.image.get_rect()
        self.plant_cls: Type[PlantT] = plant_cls
        self.rect_offset = Vector2(23,42)

    def update(self, dt: float) -> None:
        pass

    def setup_sprite(self, *args, **kwargs) -> None:
        pass

    def create_plant_instance(self, *args, **kwargs) -> AbstractPlant:
        return self.plant_cls(*args, **kwargs)
