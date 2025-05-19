from __future__ import annotations
import abc
from abc import abstractmethod
from typing import Optional

import pygame.image
import pygame_gui
from pygame import Surface, Vector2, Color

from base.sprite.game_sprite import GameSprite
from utils.utils import create_ui_manager_with_theme


class UIWidget(abc.ABC):
    object_ids: list[str] = []
    def __init__(self, object_id: str, background: Optional[Surface], size: Optional[Vector2] = Vector2(0,0), background_color: Color = Color(0,0,0,255)):
        if not self._check_object_id(object_id):
            raise ValueError(f'The id {object_id} already exists.')

        self._size: Vector2 = Vector2(0, 0)
        self.background_color = background_color
        self._screen_pos = Vector2(0, 0) # 整个UI组件在屏幕上的位置坐标
        # UI控件ID，要求唯一
        self.object_id = object_id
        # 可见性
        self.visible = True
        # 背景
        self.background: Optional[Surface] = background
        if not background and size:
            self._size = size
        elif background:
            self._size = Vector2(self.background.get_bounding_rect().size)
        self._rect = pygame.Rect(int(self.screen_pos.x), int(self.screen_pos.y), self._size.x, self._size.y)
        # 精灵容器
        self.sprite_container: Surface = Surface(self._size)
        self.sprite_container.fill(self.background_color)
        # ui manager
        from game.game import Game
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        # UI容器
        panel_rect = pygame.Rect(0, 0, self._size[0], self._size[1])
        panel_rect.topleft = tuple(self._screen_pos)
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=panel_rect,
            starting_height=1,
            manager=self.ui_manager,
            object_id=self.object_id
        )
        self.panel.background_colour = pygame.Color(0, 0, 0, 0)
        # 重建self.panel使颜色更改生效
        self.panel.rebuild()

        # 精灵对象集合
        self.sprites: list[GameSprite] = []

        self.layout()

    def _check_object_id(self, id: str) -> bool:
        """
        检查object_id是否有重复
        """
        return not id in UIWidget.object_ids

    @property
    def screen_pos(self) -> Vector2:
        return self._screen_pos

    @screen_pos.setter
    def screen_pos(self, pos: Vector2) -> None:
        self._screen_pos = pos
        self._rect.topleft = self._screen_pos
        self.panel.set_relative_position(self._screen_pos)

    @property
    def size(self) -> Vector2:
        return self._size

    @size.setter
    def size(self, size: Vector2) -> None:
        self._size = size
        self._rect.size = self._size

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    @rect.setter
    def rect(self, rec: pygame.Rect) -> None:
        self._rect = rec
        self._size = Vector2(self._rect.size)

    def setup(self, *args, **kwargs) -> None:
        self.mount()

    def destroy(self) -> None:
        self.unmount()

    @abstractmethod
    def mount(self) -> None:
        pass

    def unmount(self) -> None:
        pass

    @abstractmethod
    def layout(self) -> None:
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: Surface) -> None:
        if not self.visible:
            return
        surface.blit(self.sprite_container, self.screen_pos)
        # 将背景绘制到自身位置
        if self.background:
            self.draw_to_spr(self.background, Vector2(0, 0))
        else:
            self.sprite_container.fill(self.background_color)
        self.draw_sprites()
        self.ui_manager.draw_ui(surface)

    def draw_sprites(self):
        """
        绘制精灵对象
        """
        for spr in self.sprites:
            self.draw_to_spr(spr.image, spr.world_pos)

    def add_sprite(self, spr: GameSprite, relayout=True) -> None:
        self.sprites.append(spr)
        if relayout:
            # 添加精灵后重新布局
            self.layout()

    def process_event(self, event):
        self.ui_manager.process_events(event)

    def remove_sprite(self, spr: GameSprite, relayout=True) -> None:
        self.sprites.remove(spr)
        if relayout:
            self.layout()

    def draw_to_spr(self, image: Surface, pos: Vector2) -> None:
        self.sprite_container.blit(image, pos)