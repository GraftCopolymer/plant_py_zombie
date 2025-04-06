from __future__ import annotations

import abc
import threading

import pygame.math
from pygame import SurfaceType

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
        if len(self.scenes) > 0:
            self.scenes[-1].draw(screen)

    def push_scene(self, scene: AbstractScene):
        self.scenes.append(scene)

    def pop_scene(self):
        if len(self.scenes) > 0:
            self.scenes.pop()

    def get_scene_number(self):
        return len(self.scenes)

class AbstractScene(pygame.sprite.Group, abc.ABC):
    """
    抽象场景
    """
    def __init__(self, name: str, manager: SceneManager):
        pygame.sprite.Group.__init__(self)
        self.manager = manager
        self.manager.push_scene(self)
        self.name = name

class LevelScene(AbstractScene):
    def __init__(self, background_image: SurfaceType,name: str, manager: SceneManager):
        super().__init__(name, manager)
        self.background_image = background_image
        self.position = pygame.math.Vector2((0,0))

    def update(self, dt: float) -> None:
        super().update(dt)

    def draw(self, screen: SurfaceType, bgsurf=None, special_flags=0) -> None:
        screen.blit(self.background_image, pygame.Vector2(0,0))
        super().draw(screen, bgsurf, special_flags)

    @classmethod
    def from_path(cls, image_path: str ,name: str, manager: SceneManager):
        surface = pygame.image.load(image_path).convert_alpha()
        return cls(surface, name, manager)