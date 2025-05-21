from typing import Optional, TYPE_CHECKING, Union

import pygame.image
from pygame import Vector2

from base.game_event import ClickEvent, EventBus, StartShovelingEvent, EndShovelingEvent
from base.sprite.game_sprite import GameSprite
from game.ui.ui_widget import UIWidget
if TYPE_CHECKING:
    from game.level.level_scene import LevelScene

class Shovel(GameSprite):
    def __init__(self, group: Union[pygame.sprite.Group, list]):
        super().__init__(group, pygame.image.load('resources/ui/shovel_tool/shovel.png'))

    def update(self, dt: float) -> None:
        pass

    def setup_sprite(self, *args, **kwargs) -> None:
        pass


class ShovelSlot(UIWidget):
    def __init__(self):
        super().__init__('#shovel_slot', pygame.image.load('resources/ui/shovel_tool/shovelSlot.png'))
        self.level: Optional[LevelScene] = None
        self.screen_pos = Vector2(550, 10)
        # 铲子是否在使用中
        self.using = False
        self.shovel = Shovel([])
        # 铲子绘制在铲子槽位正中间
        self.shovel.world_pos = Vector2(self.size.x / 2 - self.shovel.rect.size[0] / 2, self.size.y / 2 - self.shovel.rect.size[1] / 2)
        self.add_sprite(self.shovel)

    def setup(self, level: 'LevelScene') -> None:
        super().setup()
        self.level = level

    def mount(self) -> None:
        EventBus().subscribe(ClickEvent, self._on_click)
        EventBus().subscribe(EndShovelingEvent, self._on_stop_shoveling)

    def unmount(self) -> None:
        EventBus().unsubscribe(ClickEvent, self._on_click)
        EventBus().unsubscribe(EndShovelingEvent, self._on_stop_shoveling)

    def layout(self) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def _on_click(self, event: 'ClickEvent') -> None:
        # 检测是否在点击范围内
        if not self.rect.collidepoint(event.mouse_pos): return
        if self.level.interaction_state.is_shoveling():
            # 正在铲植物状态，再次点击可退出铲植物状态
            # 重新显示铲子
            EventBus().publish(EndShovelingEvent())
        elif self.level.interaction_state.can_shoveling():
            # 移除铲子
            if self.shovel in self.sprites:
                self.remove_sprite(self.shovel)
                EventBus().publish(StartShovelingEvent())

    def _on_stop_shoveling(self, event: 'EndShovelingEvent'):
        # 铲子已存在，无需重复添加
        if len(self.sprites) != 0: return
        self.shovel = Shovel([])
        self.add_sprite(self.shovel)
