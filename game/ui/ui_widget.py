from __future__ import annotations
import abc
from abc import abstractmethod

import pygame.image
from pygame_gui import UIManager

from utils.utils import create_ui_manager_with_theme


class UIWidget(abc.ABC):
    def __init__(self, background_path: str):
        # 背景路径
        self.background_path = background_path
        # 背景Surface
        self.background = pygame.image.load(self.background_path)
        # 容器尺寸
        self.container_size: tuple[int, int] = self.background.get_size()
        # ui manager
        self.ui_manager = create_ui_manager_with_theme(self.container_size)
        # 子组件
        self.children: list[UIWidget] = []
        self.onCreate(self.ui_manager)
        self.layout(self)


    @abstractmethod
    def onCreate(self, ui_manager: UIManager):
        """
        构造函数最后调用，可在这里为该组件添加子组件
        添加子组件调用addChild方法，不要直接操作children数组
        """
        pass

    @abstractmethod
    def onLayout(self, context: UIWidget):
        """
        在layout最后调用
        """
        pass

    @abstractmethod
    def layout(self):
        """
        有特殊布局在这里实现, 每次ui更新都会调用该方法
        context参数为当前组件的父组件
        """
        self.onLayout()
        # 调用子组件的layout
        for child in self.children:
            child.layout()

    def addChild(self, child: UIWidget):
        self.children.append(child)


    def destroy(self):
        self.ui_manager.clear_and_reset()
        # 同时销毁子组件
        for child in self.children:
            child.destroy()
        self.children.clear()


