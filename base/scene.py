from __future__ import annotations

import abc
import threading
from abc import abstractmethod
from typing import Union

import pygame.math
from pygame import SurfaceType

from base.cameragroup import CameraGroup
from base.config import LAYERS
from base.sprite.game_sprite import GameSprite
from base.sprite.static_sprite import StaticSprite

class SceneManager:
    """
    场景管理器，单例
    """
    _instance = None
    _lock = threading.Lock()
    def __new__(cls, *args, **kwargs):
        # 确保线程安全
        if not cls._instance:
            with cls._lock:
                # 二次检查
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # self.scenes被视为栈使用
        self.scenes: list[AbstractScene] = []

    def update(self, dt: float):
        if len(self.scenes) > 0:
            self.scenes[-1].update(dt)

    def draw(self, screen: SurfaceType):
        screen.fill('black')
        if len(self.scenes) > 0:
            self.scenes[-1].draw(screen)

    def push_scene(self, scene: AbstractScene):
        self.scenes.append(scene)

    def pop_scene(self):
        if len(self.scenes) > 0:
            self.scenes.pop()

    def get_scene_number(self):
        return len(self.scenes)

class AbstractScene(abc.ABC):
    """
    抽象场景
    """
    def __init__(self, name: str, manager: SceneManager):
        self.manager = manager
        self.manager.push_scene(self)
        self.name = name

    @abstractmethod
    def update(self, dt: float) -> None: pass

    @abstractmethod
    def draw(self, screen: SurfaceType, bgsurf=None, special_flags=0) -> None: pass

    @abstractmethod
    def add(self, *sprite: Union[list[GameSprite], GameSprite]) -> None: pass

class LevelScene(AbstractScene):
    def __init__(self, background_image: SurfaceType,name: str, manager: SceneManager):
        super().__init__(name, manager)
        self.position = pygame.math.Vector2((0,0))
        self.camera = CameraGroup()
        self.background = StaticSprite(self.camera, background_image, self.position)
        self.background.z = LAYERS['background']
        self.camera.add(self.background)

    def draw(self, screen: SurfaceType, bgsurf=None, special_flags=0) -> None:
        self.camera.draw(screen, bgsurf, special_flags)

    def update(self, dt: float):
        super().update(dt)
        self.camera.update(dt)

    def set_camera(self, camera: CameraGroup):
        # 清空原相机
        self.camera.empty()
        # 将背景图添加到camera
        self.background.group = camera
        self.camera.add(self.background)

    def add(self, *sprite: Union[list[GameSprite], GameSprite]) -> None:
        self.camera.add(sprite)

    def get_group(self):
        return self.camera

    @classmethod
    def from_path(cls, image_path: str ,name: str, manager: SceneManager):
        surface = pygame.image.load(image_path).convert_alpha()
        return cls(surface, name, manager)