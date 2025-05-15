import random
from typing import Union, Optional, TYPE_CHECKING

import pygame.sprite
from pygame import Vector2

from base.animation import GifAnimation, PlayMode
from base.config import LAYERS
from base.sprite.game_sprite import GameSprite
from game.character import Position
from game.level.level_scene import LevelScene
from utils.utils import transform_coor_sys

if TYPE_CHECKING:
    from base.game_event import ClickEvent


class Sun(GameSprite):
    """
    阳光的world_pos实际为其在屏幕范围内的坐标(但不是屏幕坐标系)
    """
    # 阳光收集点的位置
    collect_point = Vector2(50, 40)
    def __init__(self, group: Union[pygame.sprite.Group, list], position: Position = Vector2(0, 0),
                 destination: Position = Vector2(0, 0)):
        self.animation = GifAnimation('resources/sun.gif', play_mode=PlayMode.LOOP, interval=50)
        super().__init__(group, self.animation.get_image(), z=LAYERS['sun'])
        self.world_pos = position
        self.rect = self.image.get_rect()
        # 该阳光将会运动到哪个位置
        self.sun_destination = destination
        self.level: Optional['LevelScene'] = None
        self.speed = 10
        # 是否处于回收状态
        self.collecting = False

    def setup_sprite(self, level: 'LevelScene') -> None:
        super().setup_sprite()
        if level.camera is not None:
            self.group = level.camera
            self.level = level
            # 根据相机坐标修正阳光坐标
            self.set_position(self.world_pos + level.camera.world_pos)
            # 修正目的地坐标
            self.sun_destination += level.camera.world_pos
            # 将自身添加到level中
            self.level.add_sun(self)

    def mount(self):
        super().mount()
        from base.game_event import EventBus, ClickEvent
        # 注册点击监听器, 一次性(阳光只能收集一次)
        EventBus().subscribe(ClickEvent, self._on_click)

    def unmount(self):
        from base.game_event import EventBus, ClickEvent
        EventBus().unsubscribe(ClickEvent, self._on_click)
        super().unmount()

    def update(self, dt: float) -> None:
        # 更新阳光动画
        self.animation.update(dt)
        self.image = self.animation.get_image()
        if self.collecting and self._arrive_des():
            # 销毁当前阳光对象
            self.level.remove_sun(self)
            self.kill()

        # 若阳光未到达目的地，则让其向目的地方向运动
        if not self._arrive_des():
            self.direction = (self.sun_destination - self.world_pos).normalize()
        else:
            self.direction = Vector2(0,0)
        self.set_position(self.world_pos + self.direction * self.speed * dt / 1000)

    def collect(self):
        """
        收集阳光, 该方法调用后, 阳光会向植物卡片栏的阳光图标处运动，到达后, 销毁阳光对象并增加阳光数量
        """
        self.collecting = True
        self.speed = 400
        self.sun_destination = Vector2(50, 40) + self.level.camera.world_pos

    def _arrive_des(self):
        return self.sun_destination.x - 5 <= self.world_pos.x <= self.sun_destination.x + 5 and self.sun_destination.y - 5 <= self.world_pos.y <= self.sun_destination.y + 5

    def _on_click(self, event: 'ClickEvent'):
        mouse_world_pos = event.get_world_pos(self.level.camera.world_pos)
        if self.rect.collidepoint(mouse_world_pos):
            self.collect()
            event.mark_handled()
            from base.game_event import EventBus, ClickEvent
            EventBus().unsubscribe(ClickEvent, self._on_click)


    @classmethod
    def at_random_pos(cls) -> 'Sun':
        """
        在指定level的随机位置生成阳光
        """
        from game.game import Game
        pos = Vector2(random.randint(0, Game.screen_size[0]), 0)
        # 目的地的横坐标应与生成位置相同(若需要不相同, 可以手动调整self.sun_destination)
        des = Vector2(pos.x, random.randint(100, 300))
        sun = cls([], pos, des)
        return sun

