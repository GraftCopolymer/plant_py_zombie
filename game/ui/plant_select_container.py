from __future__ import annotations

import copy
import json
import os.path
from typing import Optional, TYPE_CHECKING

import pygame.image
from pygame import Vector2
from pygame.rect import Rect
from pygame_gui.elements import UIVerticalScrollBar, UIButton

from game.ui.ui_widget import UIWidget

if TYPE_CHECKING:
    from base.game_event import ClickEvent, RemovePlantCardFromBankEvent
from game.ui.plant_card import PlantCard
from utils.utils import transform_coor_sys


class PlantSelectContainer(UIWidget):
    def __init__(self):
        self.scroll_offset = 0
        # PlantCard之间的间距（横竖都用该值）
        self.card_gap = 5
        self.card_list: list[PlantCard] = []
        self.view_size: Optional[Vector2] = None
        super().__init__('#plant_select_container_panel',
                         pygame.image.load('resources/background/PanelBackground_without_button.png'))
        self.screen_pos = Vector2(0, 80)
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
        self.view_size = Vector2(self.size.x, 0)
        if len(self.card_list) == 0:
            # print('警告: 卡片列表为空，停止布局')
            return
        row_size_recorder: int = 0
        row_count: int = 0
        row_height = self.card_list[0].rect.height + self.card_gap
        for card in self.card_list:
            card_and_gap = card.rect.width + self.card_gap
            if row_size_recorder + card_and_gap > self.size.x:
                row_size_recorder = 0
                row_count += 1

            card.rect_offset = Vector2(23,42)
            card.set_position(Vector2(row_size_recorder, row_count * row_height) + card.rect_offset)
            row_size_recorder += card_and_gap

        # 如果最后一行有内容，就需要 +1 行
        self.view_size.y = ((row_count + 1) * row_height if row_size_recorder > 0 else row_count * row_height)

    def setup(self):
        super().setup()
        if self.enable_scroll_bar:
            # 创建滚动条
            view_height = max(self.size.y, self.view_size.y)
            scroll_bar_rect = Rect(0, 0, 20, self.size.y)
            container_topleft = list(self.screen_pos)
            container_topleft[0] += self.size.x - scroll_bar_rect.width
            visible_ratio = self.size.y / view_height
            scroll_bar_rect.topleft = container_topleft
            self.scroll_bar = UIVerticalScrollBar(
                relative_rect=scroll_bar_rect,
                visible_percentage=visible_ratio,
                manager=self.ui_manager,
                container=self.panel,
                anchors={
                    'left': 'left',
                    'top': 'top'
                }
            )
        start_fight_rect = Rect(0, 0, 200, 50)
        start_fight_rect.bottomleft = (self.size.x / 2 - start_fight_rect.width / 2, -25)
        self.start_fight_button = UIButton(
            relative_rect=start_fight_rect,
            text='',
            manager=self.ui_manager,
            object_id='#start_fight_button',
            container=self.panel,
            anchors={
                'bottom': 'bottom',
                'left': 'left'
            }
        )


    def mount(self) -> None:
        from base.game_event import EventBus, ClickEvent, RemovePlantCardFromBankEvent
        EventBus().subscribe_ui(ClickEvent, self._on_click)
        EventBus().subscribe(RemovePlantCardFromBankEvent, self._on_resume_plant_card)

    def unmount(self):
        self.ui_manager.clear_and_reset()
        # 取消订阅的事件
        from base.game_event import EventBus, ClickEvent, RemovePlantCardFromBankEvent
        EventBus().unsubscribe(ClickEvent, self._on_click)
        EventBus().unsubscribe(RemovePlantCardFromBankEvent, self._on_resume_plant_card)
        print(f'组件PlantSelectContainer取消订阅')

    def update(self, dt: float) -> None:
        self.update_cards(dt)
        if self.scroll_bar is not None and self.enable_scroll_bar:
            factor = 1
            if self.scroll_bar.scrollable_height - self.scroll_bar.sliding_button.rect.height != 0:
                factor = (self.get_view_height() - self.size.y) / (
                            self.scroll_bar.scrollable_height - self.scroll_bar.sliding_button.rect.height)
            self.scroll_offset = self.scroll_bar.scroll_position * factor
        self.ui_manager.update(dt)

    def update_cards(self, dt: float):
        for c in self.card_list:
            c.update(dt)

    def get_view_height(self) -> int:
        return max(self.size.y, self.view_size.y)

    def draw_sprites(self):
        for card in self.card_list:
            self.draw_to_spr(card.image, card.world_pos + Vector2(0, -self.scroll_offset))

    def process_event(self, event):
        self.ui_manager.process_events(event)

    def add_card(self, plant_card: PlantCard) -> None:
        plant_card.setup_sprite()
        self.card_list.append(plant_card)
        self.add_sprite(plant_card)

    def add_all_card(self, plant_cards: list[PlantCard]):
        for c in plant_cards:
            c.setup_sprite()
        self.card_list.extend(plant_cards)
        self.sprites.extend(plant_cards)
        self.layout()

    def clear(self):
        """
        清除所有卡片
        """
        self.card_list.clear()
        self.layout()

    def _on_click(self, event: 'ClickEvent'):
        # 限定点击范围
        if not pygame.Rect(self.screen_pos.x, self.screen_pos.y, self.size.x,
                           self.size.y).collidepoint(event.mouse_pos):
            return
            # 不可见时不处理
        if not self.visible: return
        # 相对容器的鼠标坐标
        mouse_pos_in_container = transform_coor_sys(event.mouse_pos, self.screen_pos)
        # 确定点击的是哪个PlantCard
        card = None
        print(f'鼠标位置: {mouse_pos_in_container.x}, {mouse_pos_in_container.y}')
        print('卡片矩形: ')
        for c in self.card_list:
            print(f'{c.plant_cls}: {c.rect}, topleft: {c.rect.topleft}, worldpos: {c.world_pos}')
        for c in self.card_list:
            if c.rect.collidepoint(mouse_pos_in_container):
                card = c
                break
        if card is not None and not card.disabled: # 未被disable的卡片才能参与该事件
            print(f'卡片 {card.plant_cls} 被点击了')
            from base.game_event import EventBus, SelectPlantCardToBankEvent
            # 触发选择植物卡片事件, 注意此处应传卡片的副本
            card_copy = copy.copy(card)
            EventBus().publish(SelectPlantCardToBankEvent(card_copy))
            # 将该卡片设为不可用状态
            card.disable()
        # 标记为已处理
        event.mark_handled()

    def _on_resume_plant_card(self, event: 'RemovePlantCardFromBankEvent'):
        if not self.visible: return
        card = event.plant_card
        # 找到对应的被禁用的卡片
        for c in self.card_list:
            if c.plant_cls == card.plant_cls:
                # 重新启用卡片
                c.enable()

    @classmethod
    def fromFile(cls, available_plants_file_path: str) -> PlantSelectContainer:
        """
        从可选植物json文件构建
        """
        # 加载配置文件
        with open(available_plants_file_path, mode='r', encoding='utf-8') as f:
            json_obj = json.load(f)
            if json_obj is None: raise Exception(f'Error while parsing {available_plants_file_path}')
            if not isinstance(json_obj, list): raise Exception(f'Format of {available_plants_file_path} is incorrect')
            # 解析植物卡片列表
            plant_card_lis: list[PlantCard] = []
            plant_name: str
            from game.level.plant_creator import PlantCreator
            for plant_name in json_obj:
                plant_cls = PlantCreator.get_plant_cls(plant_name)
                if plant_cls is None: raise Exception(f'Plant {plant_name} does not exist')
                # 寻找 resources/card/plant_name.png 文件并加载
                filePath = f'resources/card/{plant_name}.png'
                if not os.path.isfile(filePath):
                    raise Exception(f'{filePath} 不存在')
                card_surf = pygame.image.load(filePath).convert_alpha()
                plant_card_lis.append(
                    PlantCard([], plant_cls, plant_name,card_surf)
                )
            select_container = cls()
            select_container.add_all_card(plant_card_lis)
            return select_container
