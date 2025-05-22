from __future__ import annotations

import abc
import threading
from abc import abstractmethod
from typing import Union, Optional
from pygame import Surface
from pygame_gui import UIManager
from pygame_gui.core import UIElement

class SceneManager:
    """
    场景管理器，单例
    """
    _instance = None
    _lock = threading.Lock()
    _init = False
    def __new__(cls, *args, **kwargs):
        # 确保线程安全
        if not cls._instance:
            with cls._lock:
                # 二次检查
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self.__class__._init:
            # self.scenes被视为栈使用
            self.scenes: list[AbstractScene] = []
            self.__class__._init = True

    def update(self, dt: float):
        if len(self.scenes) > 0:
            self.top().update(dt)

    def draw(self, screen: Surface):
        screen.fill('black')
        if len(self.scenes) > 0:
            self.top().draw(screen)

    def process_ui_event(self, event) -> None:
        self.top().process_ui_event(event)

    def push_scene(self, scene: AbstractScene):
        # unmount掉当前场景
        if not self.is_empty():
            self.top().unmount()
        self.scenes.append(scene)
        scene.setup_scene(self)
        self.refresh_ui()

    def pop_scene(self):
        if not self.is_empty():
            self.top().detach_scene()
            self.scenes.pop()
            self.top().setup_scene(self)
            self.refresh_ui()
            print('popped')
        else:
            raise Exception('There is no scenes')

    def pop_until(self, scene: AbstractScene, include: bool=False) -> int:
        """
        弹出栈顶到指定场景之间的所有场景
        :param scene:
        :param include: 是否弹出参数传入的指定scene，默认不弹出
        :return: 弹出的场景总数
        """
        count = 0
        if scene not in self.scenes:
            raise Exception('No such scene')
        if self.is_empty():
            raise Exception('There is no scenes')
        cur = self.top()
        while cur != scene:
            self.pop_scene()
            cur = self.top()
            count += 1
        if include:
            self.pop_scene()
            count += 1
        return count

    def refresh_ui(self):
        """
        根据当前顶层Scene重建UI
        """
        if self.is_empty():
            raise Exception('There is no scene')
        self.clear_ui_element()
        self.top().setup_ui()

    def clear_ui_element(self) -> None:
        self.top().clear_and_reset()

    def add_ui_element(self, elements: list[UIElement]) -> None:
        """
        将传入的UI元素加入当前ui_manager
        """
        for ele in elements:
            ele.ui_manager = self.top().ui_manager

    def get_scene_number(self):
        return len(self.scenes)

    def top(self) -> AbstractScene:
        if not self.is_empty():
            return self.scenes[-1]
        raise Exception('There is no scenes')

    def is_empty(self) -> bool:
        return len(self.scenes) == 0

class AbstractScene(abc.ABC):
    """
    抽象场景
    """
    def __init__(self, name: str):
        self.name = name
        self.manager: Union[SceneManager, None] = None
        self.ui_manager: Optional[UIManager] = None

    @abstractmethod
    def update(self, dt: float) -> None: pass

    @abstractmethod
    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None: pass

    @abstractmethod
    def setup_ui(self, *args, **kwargs) -> None:
        """
        每次切换到该场景时都会调用, 用于重建UI
        """
        pass

    def clear_and_reset(self):
        if self.ui_manager is not None:
            self.ui_manager.clear_and_reset()

    def setup_scene(self, manager: SceneManager) -> None:
        """
        场景初始化时调用
        """
        self.manager = manager
        self.mount()

    def process_ui_event(self, event) -> None:
        if self.ui_manager is not None:
            self.ui_manager.process_events(event)

    def detach_scene(self):
        """
        场景销毁时调用
        """
        self.unmount()

    def unmount(self):
        """
        从该场景切走时(不一定被销毁)需要执行的清理工作，例如取消订阅事件等
        """
        pass

    def mount(self):
        """
        切到场景显示时调用, 有可能是返回到该场景，也有可能是新建该场景
        """
        pass

