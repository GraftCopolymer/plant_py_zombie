import copy
from typing import Optional, Union, TYPE_CHECKING

import pygame
import pygame_gui.elements
from pygame import Surface, Vector2
from pygame_gui import UIManager
from pygame_gui.core import UIElement, IContainerLikeInterface, ObjectID
from pygame_gui.core.interfaces import IUIElementInterface

from base.config import FONT_PATH
from base.listenable import ListenableValue
from utils.utils import transform_coor_sys

if TYPE_CHECKING:
    from base.game_event import SelectPlantCardToBankEvent, ClickEvent, StartFightEvent, StopPlantEvent, PlantCardEndColdDown
from game.ui.plant_card import PlantCard



class InGamePlantSelector(UIElement):
    def __init__(
            self,
            cards: list[PlantCard],
            manager: Optional[UIManager] = None,
            container: Optional[IContainerLikeInterface] = None,
            parent_element: Optional[IUIElementInterface] = None,
            object_id: Union[ObjectID, str, None] = None
    ):
        # 加载背景图
        self.background_path = "resources/ui/in_game_plant_selector/in_game_plant_selector.png"
        self.background = pygame.image.load(self.background_path)
        rect: pygame.Rect = self.background.get_bounding_rect()
        if object_id is None:
            object_id = ObjectID(class_id="@in_game_plant_selector", object_id="#in_game_plant_selector")
        super().__init__(
            layer_thickness=1,
            starting_height=1,
            container=container,
            parent_element=parent_element,
            object_id=object_id,
            element_id=["in_game_plant_selector"],
            relative_rect=rect,
            manager=manager,
        )
        self.rect: pygame.Rect = rect
        self.blit_data[1] = self.background

        # 初始化内部容器, 创建所有本对象内部的UI组件时，请将要创建的组件的构造函数的container参数填为self.panel
        self.container_pos = pygame.Vector2(0, 0)
        panel_rect = pygame.Rect(0, 0, rect.width, rect.height)
        panel_rect.topleft = tuple(self.container_pos)
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=panel_rect,
            starting_height=1,
            manager=self.ui_manager
        )
        self.panel.background_colour = pygame.Color(0, 0, 0, 0)
        self.panel.rebuild()

        # 卡片之间的间隔
        self.card_gap = 6
        # 组件内部的Surface, 所有内部精灵将绘制在此表面上
        self.container = Surface(rect.size)

        # 最多容纳8张植物卡片
        self.max_cards_num = 8
        self.cards = cards

        # 阳光数, 可监听值, 初始为50
        self.sun_value: ListenableValue = ListenableValue(500)
        # 添加阳光监听器
        self.sun_value.add_listener(self._sun_listener)

        # 当前选择器的状态，为True时点击卡片将会进入植物放置阶段
        self.can_place_plant = False

    def setup(self):
        from base.game_event import EventBus, SelectPlantCardToBankEvent, ClickEvent, StartFightEvent, StopPlantEvent, PlantCardEndColdDown
        # 订阅从植物选择器选择植物卡片的事件
        EventBus().subscribe(SelectPlantCardToBankEvent, self._on_add_plant_card_from_selector)
        EventBus().subscribe(ClickEvent, self._on_click)
        EventBus().subscribe(StartFightEvent, self._on_level_start)
        EventBus().subscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().subscribe(PlantCardEndColdDown, self._on_plant_card_end_cold_down)

    def unmount(self):
        self.ui_manager.clear_and_reset()
        from base.game_event import EventBus, SelectPlantCardToBankEvent, ClickEvent, StartFightEvent, StopPlantEvent, \
            PlantCardEndColdDown
        # 取消事件订阅
        EventBus().unsubscribe(SelectPlantCardToBankEvent, self._on_add_plant_card_from_selector)
        EventBus().unsubscribe(ClickEvent, self._on_click)
        EventBus().unsubscribe(StartFightEvent, self._on_level_start)
        EventBus().unsubscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().unsubscribe(PlantCardEndColdDown, self._on_plant_card_end_cold_down)
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

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        surface.blit(self.container, self.container_pos)
        # 将背景绘制到自身位置
        self.container.blit(self.background, (0, 0))
        self._draw_sun_text()

        for card in self.cards:
            self.container.blit(card.image, card.world_pos)

    def _draw_sun_text(self):
        """
        绘制阳光数量文本
        """
        font = pygame.font.Font(FONT_PATH, 14)
        text = font.render(f'{self.sun_value.value}', True, pygame.Color(0, 0, 0))
        text_rect = text.get_rect()
        self.container.blit(text, Vector2(38 - text.width / 2, 75 - text.height / 2))

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
        # 重新布局
        self.layout()
        return True

    def removeCard(self, card: PlantCard) -> bool:
        if len(self.cards) == 0:
            return False
        self.cards.remove(card)
        self.layout()
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

    def _on_add_plant_card_from_selector(self, event: 'SelectPlantCardToBankEvent'):
        card = event.plant_card
        self.addCard(card)

    def _on_click(self, event: 'ClickEvent'):
        if not self.visible: return
        # 将鼠标坐标变换到容器坐标内
        mouse_pos_in_selector = transform_coor_sys(event.mouse_pos, self.container_pos)
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
                # 检查阳光是否够用
                if card.plant_cls.sun_cost > self.sun_value.value:
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
