from typing import Optional

import pygame.image
from pygame import Surface, Vector2
from pygame.rect import Rect
from pygame_gui import UIManager
from pygame_gui.elements import UIVerticalScrollBar, UIButton


from game.ui.plant_card import PlantCard
from utils.utils import create_ui_manager_with_theme


class PlantSelectContainer:
    def __init__(self):
        self.background = pygame.image.load('resources/background/PanelBackground_without_button.png')
        self.container_size = self.background.get_size()
        self.container = Surface(self.container_size)
        self.container.fill((0,0,0, 0))
        self.scroll_offset = 0
        self.ui_manager = create_ui_manager_with_theme(self.container_size)
        # PlantCard之间的间距（横竖都用该值）
        self.card_gap = 5
        self.card_list: list[PlantCard] = []
        self.view_size: Optional[Vector2] = None
        self.layout()
        # 滚动条UI
        self.scroll_bar: Optional[UIVerticalScrollBar] = None
        # 开始战斗按钮
        self.start_fight_button: Optional[UIButton] = None
        # 是否启用滚动条
        self.enable_scroll_bar = False

    def layout(self):
        """
        计算每个PlantCard的坐标并计算视图总长度
        """
        self.view_size = Vector2(self.container.width,0)
        if len(self.card_list) == 0:
            print('警告: 卡片列表为空，停止布局')
            return
        row_size_recorder: int = 0
        row_count: int = 0
        row_height = self.card_list[0].rect.height + self.card_gap
        for card in self.card_list:
            card_and_gap = card.rect.width + self.card_gap
            if row_size_recorder + card_and_gap > self.container.width:
                row_size_recorder = 0
                row_count += 1

            card.set_position(Vector2(row_size_recorder, row_count * row_height))
            row_size_recorder += card_and_gap

        # 如果最后一行有内容，就需要 +1 行
        self.view_size.y = ((row_count + 1) * row_height if row_size_recorder > 0 else row_count * row_height)

    def setup(self):
        if not self.enable_scroll_bar: return
        view_height = max(self.container.height, self.view_size.y)
        scroll_bar_rect = Rect(0, 0, 20, self.container.height)
        container_topleft = list(self.container.get_rect().topleft)
        container_topleft[0] += self.container.width - scroll_bar_rect.width
        visible_ratio = self.container.height / view_height
        scroll_bar_rect.topleft = container_topleft
        self.scroll_bar = UIVerticalScrollBar(
            relative_rect=scroll_bar_rect,
            visible_percentage=visible_ratio,
            manager=self.ui_manager,
            anchors={
                'left': 'left',
                'top': 'top'
            }
        )
        start_fight_rect = Rect(0,0,200,50)
        start_fight_rect.bottomleft = (self.container.width / 2 - start_fight_rect.width / 2, -25)
        self.start_fight_button = UIButton(
            relative_rect=start_fight_rect,
            text='',
            manager=self.ui_manager,
            object_id='#start_fight_button',
            anchors={
                'bottom': 'bottom',
                'left': 'left'
            }
        )

    def kill(self):
        if self.start_fight_button:
            self.start_fight_button.kill()
            self.start_fight_button = None
        if self.scroll_bar:
            self.scroll_bar.kill()
            self.scroll_bar = None

    def update(self, dt: float) -> None:
        # from game.game import Game
        self.ui_manager.update(dt)
        if self.scroll_bar is not None and self.enable_scroll_bar:
            factor = 1
            if self.scroll_bar.scrollable_height - self.scroll_bar.sliding_button.rect.height != 0:
                factor = (self.get_view_height() - self.container.height) / (self.scroll_bar.scrollable_height - self.scroll_bar.sliding_button.rect.height)
            self.scroll_offset = self.scroll_bar.scroll_position * factor

    def get_view_height(self) -> int:
        return max(self.container.height, self.view_size.y)

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        screen.blit(self.container, Vector2(0,0))
        self.container.blit(self.background, Vector2(0,0))
        for card in self.card_list:
            self.container.blit(card.image, card.world_pos + Vector2(0, -self.scroll_offset) + card.rect_offset)
        self.ui_manager.draw_ui(screen)

    def process_event(self, event):
        self.ui_manager.process_events(event)

    def add_card(self, plant_card: PlantCard) -> None:
        plant_card.setup_sprite()
        self.card_list.append(plant_card)
        # 重新计算布局
        self.layout()
