import abc
from abc import abstractmethod
from typing import Union

import pygame.sprite
from pygame import Surface, Vector2

from game.character import Position
from base.config import LAYERS

class GameSprite(pygame.sprite.Sprite, abc.ABC):
    """
    游戏精灵
    """
    def __init__(self, group: Union[pygame.sprite.Group, list], image: Union[Surface, None], position: Position = pygame.math.Vector2((0,0)), speed: int = 0, z: int = LAYERS['main']):
        pygame.sprite.Sprite.__init__(self, group)
        self.group = group
        self.world_pos = position
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = speed
        self.rect: Union[pygame.Rect, None] = None
        self.image = image
        self.z = z
        # 图片偏移（由于有些gif图有大量透明像素，图片矩形并不适合用来做碰撞检测，所以图片需要和矩形框分开计算，该变量是为了将图片与矩形框对齐的偏移量）
        self.image_offset: pygame.Vector2 = pygame.Vector2(0, 0)
        self.rect_offset: pygame.Vector2 = pygame.Vector2(0,0)
        self._old_rect_offset: Vector2 = self.rect_offset
        # 是否显示
        self.display = True

    @abstractmethod
    def update(self, dt: float) -> None:
        if self.rect is None: return
        self.rect.topleft = self.world_pos
        # if self.rect_offset.x != self._old_rect_offset.x or self.rect_offset.y != self._old_rect_offset.y:
        #     self.rect.move_ip(self._old_rect_offset)
        #     self.world_pos += self._old_rect_offset
        #     self.rect.move_ip(-self.rect_offset)
        #     self.world_pos -= self.rect_offset
        #     self._old_rect_offset = self.rect_offset

    @abstractmethod
    def setup_sprite(self, *args, **kwargs) -> None:
        """
        该方法由子类重写，用于延迟挂载对象
        """
        pass

    def debug_draw(self, surface: Surface, camera_pos: Vector2) -> None:
        """
        用于绘制debug图形
        :param surface: 绘制表面，由相机传入
        :param camera_pos: 相机位置
        """
        pass

    def get_z(self):
        return self.z

    def set_position(self, position: Position):
        pos = position.copy()
        self.world_pos = pos
        if self.rect is None: return
        self.move_rect_to(pos)

    def set_center_pos(self, pos: pygame.Vector2) -> None:
        if self.rect is None: raise Exception("the sprite don't have a rect")
        self.rect.center = tuple(pos)
        self.world_pos = pygame.Vector2(self.rect.topleft)

    def get_center_pos(self) -> pygame.Vector2:
        if self.rect is None:
            raise Exception("the sprite don't have a rect")
        return pygame.Vector2(self.rect.center)

    def move_rect_to(self, topleft: pygame.Vector2):
        if self.rect is not None:
            self.rect.topleft = topleft.copy()


