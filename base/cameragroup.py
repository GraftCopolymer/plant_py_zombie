import abc
from abc import abstractmethod
from typing import Union

import pygame.sprite
from pygame import Surface, Vector2

from base.sprite.game_sprite import GameSprite


class CameraGroup(pygame.sprite.Group):
    """
    游戏相机, 负责视角移动和图层管理
    想要一个对象显示在视口内，需要调用相机对象的add方法
    """
    def __init__(self):
        super().__init__(self)
        self.animator: Union[CameraAnimator, None] = None
        # 相机所在的世界坐标位置
        self.world_pos: Vector2 = Vector2(0,0)

    def update(self, dt: float):
        """
        相机更新，注意，相机只负责其自己的更新，显示的内容的更新由Scene完成
        """
        super().update(dt)
        if self.animator:
            self.animator.update(dt)
        sprite: GameSprite
        # for sprite in self.sprites():
        #     sprite.camera_offset = self.world_pos.copy()

    def move_to(self, pos: pygame.Vector2):
        self.world_pos = pos

    def animate_to(self, offset: pygame.Vector2):
        self.animator.animate_to(offset, 1000, EaseInOutQuad())

    def draw_debug(self, surface: Surface, sprite: GameSprite, bgsurf=None, special_flags=0) -> None:
        """
        绘制Debug图形, 仅在Game.debug_mode = True时生效
        """
        sprite.debug_draw(surface, camera_pos=self.world_pos)
        pygame.draw.circle(surface, 'blue', sprite.world_pos - self.world_pos, 2)
        pygame.draw.circle(surface, 'lightblue', sprite.get_center_pos() - self.world_pos, 2)

    def draw(self, surface: Surface, bgsurf=None, special_flags=0):
        layers_sprites: dict[int, list[GameSprite]] = {}
        for spr in self.sprites():
            if spr.get_z() not in layers_sprites:
                layers_sprites[spr.get_z()] = []
            layers_sprites[spr.get_z()].append(spr)
        layers = list(layers_sprites.keys())
        layers.sort()

        layer: int
        for layer in layers:
            # 依次绘制每一图层
            sprite: GameSprite
            for sprite in layers_sprites[layer]:
                if not sprite.display: continue
                # surface.blit(sprite.image, sprite.world_pos - sprite.image_offset)
                surface.blit(sprite.image, sprite.world_pos - sprite.image_offset - self.world_pos)
                from game.game import Game
                if Game.debug_mode:
                    self.draw_debug(surface, sprite, bgsurf, special_flags)

class EasingFunction(abc.ABC):
    """
    相机运动速率函数类
    """
    @abstractmethod
    def ease(self, t: float) -> float:
        """
        t为一个0~1之间的值
        请返回一个经过本函数映射后的一个0~1之间的值
        """
        pass

class EaseInOutQuad(EasingFunction):
    def ease(self, t: float) -> float:
        return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t

class CameraAnimator:
    def __init__(self, camera: CameraGroup, duration: float, easing: EasingFunction):
        self.camera = camera
        self.duration = duration
        self.easing = easing
        self.elapsed = 0
        self.running = False
        self.start_offset = pygame.Vector2(0, 0)
        self.end_offset = pygame.Vector2(0, 0)

    def animate_to(self, new_offset: pygame.Vector2, duration: float, easing: EasingFunction):
        self.start_offset = self.camera.world_pos.copy()
        self.end_offset = new_offset
        self.duration = duration
        self.easing = easing
        self.elapsed = 0
        self.running = True

    def update(self, dt: float):
        if not self.running:
            return

        self.elapsed += dt
        t = min(self.elapsed / self.duration, 1)
        eased_t = self.easing.ease(t)
        new_offset = self.start_offset.lerp(self.end_offset, eased_t)
        self.camera.world_pos = new_offset

        if t >= 1:
            self.running = False


