from __future__ import annotations
import abc
import threading
from typing import Dict, List, Protocol, Type, TypeVar, Optional, TYPE_CHECKING, Union, runtime_checkable

import pygame
import pygame_gui.elements
from pygame import Vector2

from base.scene import SceneManager

if TYPE_CHECKING:
    from game.character.plant import AbstractPlant
    from base.game_grid import AbstractPlantCell
    from game.character.zombie import AbstractZombie
    from game.ui.plant_card import PlantCard
    from game.level.sun import Sun
    from game.level.level_scene import LevelScene


T = TypeVar("T", bound="Event")

@runtime_checkable
class EventHandler(Protocol[T]):
    def __call__(self, event: T) -> None: ...


class Subscription:
    def __init__(self, handler: EventHandler[T], priority: int = 0, once: bool = False):
        self.handler = handler
        self.priority = priority
        self.once = once


class EventBus:
    """
    全局事件总线，支持：
    优先级
    一次性订阅
    多级继承事件派发
    """
    _instance: Optional[EventBus] = None
    _lock = threading.Lock()

    def __new__(cls) -> EventBus:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers: Dict[Type[Event], List[Subscription]] = {}
            return cls._instance

    def process_event(self):
        # print(f"当前队列处理器个数: {len([handler for sh in self._subscribers.values() for handler in sh])}")
        for event in pygame.event.get():
            SceneManager().process_ui_event(event)
            self._dispatch_event(event)
            if event.type == pygame.QUIT:
                from game.game import Game
                Game.end()

    def _dispatch_event(self, event: pygame.event.Event) -> None:
        """
        派发事件
        :param event: 根据该参数指定的事件类型向事件总线派发事件
        """
        if event.type == pygame.MOUSEMOTION:
            event = MouseMotionEvent(pygame.Vector2(event.pos), pygame.Vector2(event.rel))
            EventBus().publish(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            event = ClickEvent(pygame.Vector2(event.pos))
            EventBus().publish(event)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            EventBus().publish(ButtonClickEvent(event.ui_element))
        elif event.type == pygame.KEYDOWN:
            EventBus().publish(KeyDownEvent(event.key))

    def subscribe(self, event_type: Type[T], handler: EventHandler[T],
                  priority: int = 0, once: bool = False) -> Subscription:
        """订阅事件，支持优先级和一次性订阅"""
        subscription = Subscription(handler, priority, once)
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        subscribers = self._subscribers[event_type]
        # 按优先级降序插入
        index = next((i for i, sub in enumerate(subscribers)
                      if sub.priority < priority), len(subscribers))
        subscribers.insert(index, subscription)
        return subscription

    def subscribe_ui(self, event_type: Type[T], handler: EventHandler[T], once: bool = False) -> None:
        """
        订阅UI事件，会比普通事件优先处理
        """
        self.subscribe(event_type, handler, priority=100, once=once)

    def unsubscribe(self, event_type: Type[T], handler: Union[EventHandler[T], Subscription]) -> None:
        """取消订阅"""
        if event_type in self._subscribers:
            subs = self._subscribers[event_type]
            if isinstance(handler, EventHandler):
                # 移除所有匹配的handler
                self._subscribers[event_type] = [
                    sub for sub in subs if sub.handler != handler
                ]
            elif isinstance(handler, Subscription):
                self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """发布事件，支持冒泡和继承链处理"""
        # 获取事件类型的继承链（排除非Event父类）
        event_types = [cls for cls in type(event).mro()
                       if issubclass(cls, Event) and cls is not Event]

        for event_type in event_types:
            if event.handled:
                break

            if event_type not in self._subscribers:
                continue

            # 使用副本遍历以防修改原列表
            for sub in list(self._subscribers[event_type]):
                if event.handled:
                    break

                # 执行处理程序
                sub.handler(event)

                # 处理一次性订阅
                if sub.once:
                    try:
                        self._subscribers[event_type].remove(sub)
                    except ValueError:
                        pass


class Event(abc.ABC):
    """事件基类"""

    def __init__(self) -> None:
        self.handled = False

    def mark_handled(self) -> None:
        """标记为已处理"""
        self.handled = True

# UI事件
class UIEvent(Event):
    def __init__(self, ui_element: pygame_gui.core.UIElement):
        super().__init__()
        self.ui_element = ui_element

class ButtonClickEvent(UIEvent):
    def __init__(self, target: pygame_gui.elements.UIButton):
        super().__init__(target)

# 游戏事件
class MouseEvent(Event):
    def __init__(self, mouse_pos: pygame.Vector2):
        super().__init__()
        self.mouse_pos = mouse_pos

    def get_world_pos(self, camera_pos: Vector2) -> Vector2:
        """
        获取点击位置的世界坐标
        :param camera_pos: 相机位置，用于计算世界坐标
        :return: 点击位置的世界坐标
        """
        return self.mouse_pos + camera_pos

class KeyDownEvent(Event):
    """
    键盘某个键按下事件
    """
    def __init__(self, key: int):
        super().__init__()
        self.key: int = key

class ClickEvent(MouseEvent):
    def __init__(self, mouse_pos: pygame.Vector2):
        super().__init__(mouse_pos)

class HoverEvent(MouseEvent):
    def __init__(self, mouse_pos: pygame.Vector2, target):
        super().__init__(mouse_pos)
        self.target = target

class MouseMotionEvent(MouseEvent):
    def __init__(self, mouse_pos: pygame.Vector2, last_pos: pygame.Vector2):
        """
        鼠标运动事件
        :param mouse_pos: 当前鼠标位置
        :param last_pos: 上次鼠标位置
        """
        super().__init__(mouse_pos)
        self.last_pos = last_pos



class StartPlantEvent(Event):
    """
    开始种植植物事件
    """
    def __init__(self, plant: AbstractPlant):
        super().__init__()
        self.plant = plant

class StopPlantEvent(Event):
    """
    结束种植植物事件, 该事件触发后请勿再从PlantingState中获取植物对象
    """
    def __init__(self, plant: AbstractPlant, cell: AbstractPlantCell):
        super().__init__()
        self.plant = plant
        self.cell = cell

class WillGenZombieEvent(Event):
    def __init__(self, zombie: AbstractZombie, row: int):
        super().__init__()
        self.zombie = zombie
        self.row = row

class NextLevelEvent(Event):
    def __init__(self, level: 'LevelScene'):
        super().__init__()
        self.next_level = level

class StartFightEvent(Event):
    def __init__(self):
        super().__init__()

class SelectPlantCardToBankEvent(Event):
    def __init__(self, plant_card: 'PlantCard'):
        super().__init__()
        self.plant_card = plant_card

class RemovePlantCardFromBankEvent(Event):
    def __init__(self, plant_card: 'PlantCard'):
        super().__init__()
        self.plant_card = plant_card

class PlantCardStartColdDown(Event):
    """
    植物卡片开始冷却
    """
    def __init__(self, card: 'PlantCard'):
        super().__init__()
        self.plant_card = card

class PlantCardEndColdDown(Event):
    """
    植物卡片冷却结束
    """
    def __init__(self, card: 'PlantCard'):
        super().__init__()
        self.plant_card = card

class SunCollectEvent(Event):
    def __init__(self, sun: 'Sun'):
        super().__init__()
        self.sun = sun

class StartShovelingEvent(Event):
    def __init__(self):
        super().__init__()

class EndShovelingEvent(Event):
    def __init__(self):
        super().__init__()