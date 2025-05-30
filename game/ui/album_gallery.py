from collections.abc import Callable
from typing import Optional

import pygame
import pygame_gui.elements
from pygame import Vector2, Surface, Color, SRCALPHA

from base.game_event import ButtonClickEvent, EventBus, ClickEvent
from base.scene import SceneManager
from base.sprite.static_sprite import StaticSprite
from game.ui.intro_page import IntroPage
from game.ui.title_content_widget import TitleContentWidget
from game.ui.ui_widget import UIWidget
from utils.utils import render_multiline_text


class AlbumGallery(UIWidget):
    """
    显示图鉴的每一项内容, 自动换行
    """
    def __init__(self, size: Vector2, on_back_button_pressed: Optional[Callable[..., None]] = None, gap: int = 20, padding: int = 90):
        """
        :param gap: 展示项之间的间隔(同时应用于上下间隔和左右间隔)
        :param padding: 上、左、右的边距, 注意，不保证右边距一定是这个值，具体原因见布局逻辑
        """
        self.padding: int = padding
        self.gap = gap
        self.display_items: list[TitleContentWidget] = []
        super().__init__(object_id='album_gallery', background_color=Color(0,25,0), background=None, size=size)
        self.on_back_button_pressed = on_back_button_pressed

    def setup(self) -> None:
        super().setup()
        back_button_rect = pygame.Rect(0,0,100,50)
        back_button_rect.topleft = (20, 20)
        pygame_gui.elements.UIButton(
            relative_rect=back_button_rect,
            manager=self.ui_manager,
            container=self.panel,
            text='关闭',
            anchors={
                'left': 'left',
                'top': 'top'
            },
            object_id='#gallery_back_button'
        )

    def draw(self, surface: Surface) -> None:
        super().draw(surface)

    def mount(self) -> None:
        EventBus().subscribe(ButtonClickEvent, self._on_button_clicked)
        EventBus().subscribe(ClickEvent, self._on_mouse_click)

    def unmount(self) -> None:
        self.ui_manager.clear_and_reset()
        EventBus().unsubscribe(ButtonClickEvent, self._on_button_clicked)
        EventBus().unsubscribe(ClickEvent, self._on_mouse_click)

    def layout(self) -> None:
        if not self.display_items:
            return

        cur_x = self.padding
        cur_y = self.padding
        current_line_max_height = 0  # 记录当前行的最高元素高度

        # 遍历 TitleContentWidget 实例，计算它们在 AlbumGallery 中的相对位置
        for i, item in enumerate(self.display_items):
            # 获取 item 的实际渲染尺寸，以便正确计算布局
            # 注意：TitleContentWidget 的 size 属性在它自己的 __init__ 中已经根据其内部内容设置了
            item_width = item.size.x
            item_height = item.size.y

            # 更新当前行的最大高度
            current_line_max_height = max(current_line_max_height, item_height)

            # 检查是否需要换行
            # 这里应使用 AlbumGallery 自身的尺寸 self.size.x 作为可用宽度
            if cur_x != self.padding and (cur_x + item_width + self.gap) > (self.size.x - self.padding):
                # 换行
                cur_x = self.padding
                cur_y += current_line_max_height + self.gap
                current_line_max_height = item_height  # 换行后，新行的最大高度从当前元素开始

            # 设置当前 TitleContentWidget 实例的 screen_pos
            # 这个位置是相对于 AlbumGallery 左上角的
            item.screen_pos = Vector2(cur_x, cur_y)

            # 移动到下一个元素的起始X坐标
            cur_x += item_width + self.gap

        # 调整 AlbumGallery 自身的 rect.height 以便能够完全包容所有内容
        # 如果 cur_y 还没有内容，则至少是 padding 的两倍
        if self.display_items:
            self.rect.height = cur_y + current_line_max_height + self.padding
        else:
            self.rect.height = self.padding * 2  # 或者一个默认的最小高度

        # 确保 AlbumGallery 的 rect 宽度正确
        self.rect.width = self.size.x  # 假设 Gallery 宽度是固定传入的 size.x

    def set_content(self, widget_list: list[TitleContentWidget]):
        self.display_items = widget_list
        self.sprites.clear()  # 清空旧的精灵

        # 先执行布局，计算出每个 TitleContentWidget 的正确位置
        self.layout()

        # 根据布局后的位置，创建并添加 StaticSprite
        for item in self.display_items:
            # item.get_surface() 已经包含了 TitleContentWidget 内部的布局
            # item.screen_pos 在 layout() 中已经被计算并设置了
            surf = item.get_surface()
            self.add_sprite(StaticSprite([], surf, item.screen_pos), relayout=False)
            # 这里 relayout=False 是因为 AlbumGallery 自身的布局已经完成了


    def _on_button_clicked(self, event: 'ButtonClickEvent'):
            if '#gallery_back_button' in event.ui_element.object_ids:
                if self.on_back_button_pressed is not None:
                    self.on_back_button_pressed()

    def _on_mouse_click(self, event: 'ClickEvent'):
        mouse_pos = event.mouse_pos
        # 检测哪个条目被点击了
        target: Optional[TitleContentWidget] = None
        for item in self.display_items:
            if item.rect.collidepoint(mouse_pos):
                target = item
                break
        if target is not None and target.extra is not None and isinstance(target.extra, dict):
            title_img = target.title.image
            name = target.extra['name']
            name_surf = pygame.Font('resources/ui/STHeiti Light.ttc', 20).render(name, True, Color(255,255,255,255))
            title_surf = Surface((max(title_img.width, name_surf.width), title_img.height + name_surf.height + 5), SRCALPHA)
            title_surf.blit(title_img, (title_surf.width / 2 - title_img.width / 2, 0))
            title_surf.blit(name_surf, (title_surf.width / 2 - name_surf.width / 2, 5 + title_img.height))
            font = pygame.Font('resources/ui/STHeiti Light.ttc', size=14)
            content_text_surf = render_multiline_text(target.extra['intro'], font, Color(255,255,255,255), 200)
            # 打开被点击项的介绍页面
            SceneManager().push_scene(IntroPage(title_surf, content_text_surf))


