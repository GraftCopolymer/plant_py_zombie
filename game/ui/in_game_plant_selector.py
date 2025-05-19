import copy
from typing import Union, TYPE_CHECKING

import pygame
from pygame import Vector2, Surface
from pygame_gui.core import ObjectID

from base.config import FONT_PATH
from base.listenable import ListenableValue
from game.ui.ui_widget import UIWidget
from utils.utils import transform_coor_sys

if TYPE_CHECKING:
    from base.game_event import SelectPlantCardToBankEvent, ClickEvent, StartFightEvent, StopPlantEvent, \
    PlantCardEndColdDown, SunCollectEvent
from game.ui.plant_card import PlantCard


class InGamePlantSelector(UIWidget):
    def __init__(
            self,
            cards: list[PlantCard],
            object_id: Union[ObjectID, str, None] = None
    ):
        # 加载背景图
        self.background_path = "resources/ui/in_game_plant_selector/in_game_plant_selector.png"
        if object_id is None:
            object_id = "#in_game_plant_selector"
            # 卡片之间的间隔
            self.card_gap = 6

            # 最多容纳8张植物卡片
            self.max_cards_num = 8
            self.cards = cards

            # 阳光数, 可监听值, 初始为50
            self.sun_value: ListenableValue = ListenableValue(500)
            # 添加阳光监听器
            self.sun_value.add_listener(self._sun_listener)

            # 当前选择器的状态，为True时点击卡片将会进入植物放置阶段
            self.can_place_plant = False
        super().__init__(
            object_id, pygame.image.load(self.background_path)
        )

    def mount(self) -> None:
        from base.game_event import EventBus, SelectPlantCardToBankEvent, ClickEvent, StartFightEvent, StopPlantEvent, \
            PlantCardEndColdDown, SunCollectEvent
        # 订阅从植物选择器选择植物卡片的事件
        EventBus().subscribe(SelectPlantCardToBankEvent, self._on_add_plant_card_from_selector)
        EventBus().subscribe(ClickEvent, self._on_click)
        EventBus().subscribe(StartFightEvent, self._on_level_start)
        EventBus().subscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().subscribe(PlantCardEndColdDown, self._on_plant_card_end_cold_down)
        # 阳光收集事件
        EventBus().subscribe(SunCollectEvent, self._on_collect_sun)

    def unmount(self):
        self.ui_manager.clear_and_reset()
        from base.game_event import EventBus, SelectPlantCardToBankEvent, ClickEvent, StartFightEvent, StopPlantEvent, \
            PlantCardEndColdDown, SunCollectEvent
        # 取消事件订阅
        EventBus().unsubscribe(SelectPlantCardToBankEvent, self._on_add_plant_card_from_selector)
        EventBus().unsubscribe(ClickEvent, self._on_click)
        EventBus().unsubscribe(StartFightEvent, self._on_level_start)
        EventBus().unsubscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().unsubscribe(PlantCardEndColdDown, self._on_plant_card_end_cold_down)
        EventBus().unsubscribe(SunCollectEvent, self._on_collect_sun)
        print(f'组件InGamePlantSelector取消订阅')

    def layout(self):
        length = len(self.cards)
        cur_pos = pygame.Vector2(0, 0)
        # 调整卡片位置
        for index in range(length):
            self.cards[index].rect_offset = Vector2(81, 9)
            self.cards[index].set_position(cur_pos.copy() + self.cards[index].rect_offset)
            if index != length - 1:
                cur_pos += pygame.Vector2(self.card_gap + self.cards[index].rect.width, 0)

    def draw(self, surface: Surface):
        super().draw(surface)
        self._draw_sun_text()

    def _draw_sun_text(self):
        """
        绘制阳光数量文本
        """
        font = pygame.font.Font(FONT_PATH, 14)
        text = font.render(f'{self.sun_value.value}', True, pygame.Color(0, 0, 0))
        self.draw_to_spr(text, Vector2(38 - text.width / 2, 75 - text.height / 2))

    def update(self, dt: float):
        self.update_cards(dt)

    def update_cards(self, dt: float):
        for c in self.cards:
            c.update(dt)

    def addCard(self, card: PlantCard) -> bool:
        """
        添加植物卡片，成功返回True，否则返回False
        :param card:
        :return:
        """
        if len(self.cards) >= self.max_cards_num:
            return False
        self.cards.append(card)
        self.add_sprite(card)
        return True

    def removeCard(self, card: PlantCard) -> bool:
        if len(self.cards) == 0:
            return False
        self.cards.remove(card)
        self.remove_sprite(card)
        return True

    def removeCardAt(self, index: int) -> bool:
        if len(self.cards) == 0:
            return False
        self.cards.pop(index)
        self.layout()
        return True

    def _sun_listener(self):
        """
        阳光数量监听器
        """
        # 遍历所有卡片, 将无法种植的卡片disable()
        for card in self.cards:
            if card.plant_cls.sun_cost > self.sun_value.value:
                card.disable()
            else:
                card.enable()

    def _on_add_plant_card_from_selector(self, event: 'SelectPlantCardToBankEvent'):
        card = event.plant_card
        self.addCard(card)

    def _on_click(self, event: 'ClickEvent'):
        if not self.visible: return
        # 将鼠标坐标变换到容器坐标内
        mouse_pos_in_selector = transform_coor_sys(event.mouse_pos, self.screen_pos)
        # 检测哪个卡片被选中了
        card = None
        for c in self.cards:
            if c.rect.collidepoint(mouse_pos_in_selector):
                card = c
                break
        if card is not None:
            print(f'InGamePlantSelector: 点击了: {card.plant_cls}')
            from base.game_event import EventBus, RemovePlantCardFromBankEvent, StartPlantEvent
            if not self.can_place_plant:
                if card.rect.collidepoint(mouse_pos_in_selector):
                    # 删除被点到的卡片
                    self.removeCard(card)
                    EventBus().publish(RemovePlantCardFromBankEvent(copy.copy(card)))
            else:
                from game.level.plant_creator import PlantCreator
                # 检查阳光是否够用以及是否处于冷却状态和禁用状态
                if card.plant_cls.sun_cost > self.sun_value.value or card.cold_down or card.disabled:
                    return
                plant = PlantCreator.create_plant(card.plant_name)
                EventBus().publish(StartPlantEvent(plant))

    def _on_level_start(self, event: 'StartFightEvent'):
        # 修改植物种植状态
        self.can_place_plant = True

    def _on_stop_planting(self, event: 'StopPlantEvent'):
        plant = event.plant
        if plant is not None:
            # 扣除阳光
            self.sun_value.value = self.sun_value.value - plant.sun_cost
            # 禁用卡片并开始冷却
            for c in self.cards:
                if c.plant_cls == plant.__class__:
                    c.disable()
                    c.cold_down_start()
                    break

    def _on_plant_card_end_cold_down(self, event: 'PlantCardEndColdDown'):
        card = event.plant_card
        if self.sun_value.value >= card.plant_cls.sun_cost:
            card.enable()

    def _on_collect_sun(self, event: 'SunCollectEvent'):
        self.sun_value.value = self.sun_value.value + event.sun.value
