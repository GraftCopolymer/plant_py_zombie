from typing import Optional

import pygame.image
from pygame import Surface, Vector2, Color, SRCALPHA

from base.sprite.game_sprite import GameSprite
from base.sprite.static_sprite import StaticSprite
from game.ui.ui_widget import UIWidget


class TitleContentWidget(UIWidget):
    """
    标题在上, 内容在下的通用展示型UI
    """
    def __init__(self, title: Surface, content: Surface, size: Optional[Vector2], gap: int=5, extra=None):
        """
        :param title: 标题
        :param content: 内容
        :param gap: 标题和内容的间隔距离
        :param size: 整个组件的尺寸，不传则以width: max(title.width, content.width) + gap, height: title.height + content.height为准
        """
        self.title: GameSprite = StaticSprite([], title, Vector2(0, 0))
        self.content: GameSprite = StaticSprite([], content, Vector2(0, 0))
        self.gap = gap
        s = None
        if size is not None:
            s = size
        else:
            s = Vector2(max(title.width, content.width), title.height + content.height + self.gap)

        # 额外信息
        self.extra = extra
        super().__init__('title_content_widget', None, size=s, background_color=Color(255,255,255,0))
        # 记录以渲染
        self.add_sprite(self.title, relayout=False)
        self.add_sprite(self.content)

    def draw(self, surface: Surface) -> None:
        super().draw(surface)

    def mount(self) -> None:
        pass

    def layout(self) -> None:
        # Title 居中在顶部
        title_x = (self.size.x - self.title.rect.width) / 2
        self.title.set_position(Vector2(title_x, 0))

        # Content 位于 Title 下方，并居中
        content_y = self.gap + self.title.rect.height
        content_x = (self.size.x - self.content.rect.width) / 2
        self.content.set_position(Vector2(content_x, content_y))

    def get_surface(self) -> Surface:
        container = Surface(self.size, SRCALPHA)
        # 暂时改变整体组件的坐标
        # 暂存现有坐标
        origin_pos = self.screen_pos
        self.screen_pos = Vector2(0,0)
        self.draw(container)
        # 恢复原来坐标
        self.screen_pos = origin_pos
        return container