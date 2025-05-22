from __future__ import annotations
import abc
import json
import os.path
import random
import threading
from abc import abstractmethod
from typing import Literal, Any, List

import pygame

from base.animation import Animation, AnimationLoader

ConfigType = Literal['zombie', 'animation']
class ConfigManager:
    """
    配置文件管理器，单例，任何配置文件都需要从该管理器读取
    内部实现了一些防止重复加载配置的逻辑
    """
    _instance = None
    _lock = threading.Lock()
    # 配置id到配置对象的映射
    _configs: dict[str, GameSpriteConfig] = {}
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_config(self, config_id: str) -> GameSpriteConfig:
        """
        在调用该方法前请确保配置文件已经被加载
        :param config_id: 配置id
        :return:
        """
        if config_id in self._configs:
            return self._configs[config_id]
        raise Exception("The Config {} haven't been loaded yet".format(config_id))

    def get_zombie_config(self, config_id: str) -> ZombieConfig:
        if config_id in self._configs:
            config = self._configs[config_id]
            if isinstance(config, ZombieConfig): return config
            raise Exception('The config {} is not instance of ZombieConfig'.format(config_id))
        raise Exception("The config {} haven't been loaded yet".format(config_id))

    def get_animation_config(self, config_id: str) -> AnimationConfig:
        if config_id in self._configs:
            config = self._configs[config_id]
            if isinstance(config, AnimationConfig): return config
            raise Exception('The config {} is not instance of AnimationConfig'.format(config_id))
        raise Exception("The config {} haven't been loaded yet".format(config_id))

    def load(self, config_type: ConfigType, path: str) -> None:
        """
        加载指定的配置文件
        :param config_type:
        :param path:
        :return:
        """
        config = GameSpriteConfig.load_config(path, config_type)
        if self.exists(config.get_id()): raise Exception("Try to load config repeatedly")
        self._configs[config.get_id()] = config

    def exists(self, config_id: str) -> bool:
        if config_id in self._configs:
            return True
        else:
            return False


class GameSpriteConfig(abc.ABC):
    def __init__(self, path: str):
        self.path = path

    @abstractmethod
    def parse(self, path: str) -> None:
        """
        子类应重写该方法以解析自己的配置文件
        :param path: 配置文件路径
        """
        pass

    @abstractmethod
    def get_id(self) -> str:
        """
        返回配置文件id，子类需重写
        :return:
        """
        pass

    @classmethod
    def load_config(cls, path: str, config_type: ConfigType) -> GameSpriteConfig:
        if config_type == "zombie":
            config = ZombieConfig(path)
        elif config_type == "animation":
            config = AnimationConfig(path)
        else:
            raise Exception("Invalid config type!")
        return config

class ZombieConfig(GameSpriteConfig):
    def __init__(self, path: str):
        super().__init__(path)
        self.animation = None
        self.max_health: float = 0
        self.min_health: float = 0
        self.config_id: str = ''
        self.init_state: str = ''
        self.speed: int = 0
        self.zombie_offset: pygame.Vector2 = pygame.Vector2(0,0)
        # 解析配置文件
        self.parse(path)

    def parse(self, path: str) -> None:
        with open(path) as f:
            json_data = json.load(f)
            directory: str = os.path.dirname(path)
            if "id" not in json_data or len(json_data['id']) == 0:
                raise Exception("The config has no config id or the id is empty")
            self.config_id = json_data['id']
            if "animation" not in json_data:
                raise Exception("Zombie config must have animations")
            if "health" not in json_data:
                raise Exception("Zombie config must have health")
            if 'speed' not in json_data:
                raise Exception("The speed must be provided")
            if "max" not in json_data['health'] or "min" not in json_data['health']:
                raise Exception("Invalid health info")
            if 'zombie_offset' in json_data:
                if not isinstance(json_data['zombie_offset'], list): raise Exception('Invalid zombie offset')
                offset = json_data['zombie_offset']
                self.zombie_offset = pygame.Vector2(offset[0], offset[1])
            self.animation = AnimationConfig(os.path.join(directory, json_data['animation']))
            self.min_health = json_data['health']['min']
            self.max_health = json_data['health']['max']
            assert self.min_health <= self.max_health # 需要保证最小生命值小于等于最大生命值
            self.speed = json_data['speed']

    def get_id(self) -> str:
        return self.config_id


class AnimationConfig(GameSpriteConfig):
    def __init__(self, path: str):
        super().__init__(path)
        self.config_id: str = ''
        self.root_path: str = ''
        self.animations: dict[str, list[dict[str, Any]]] = {}
        self.init_state: str = ''
        self.parse(path)

    def parse(self, path: str) -> None:
        with open(path) as f:
            json_data = json.load(f)
            directory: str = os.path.dirname(path)
            offset = pygame.Vector2(0,0)
            if "id" not in json_data or len(json_data['id']) == 0:
                raise Exception("The config has no config id or the id is empty")
            self.config_id = json_data['id']
            if "animations" not in json_data:
                raise Exception("Zombie config must have animations")
            # 解析动画
            self.animations = json_data['animations']
            self.root_path = directory
            # 初始状态默认为第一个读取的状态
            self.init_state = list(self.animations.keys())[0]

    def get_random_animation_of_state(self, state: str):
        animations = AnimationLoader.load(self.animations, self.root_path)
        if state not in self.animations: raise Exception("No such state: {}".format(state))
        return random.choice(animations[state])

    def get_random_animation_group(self) -> dict[str, Animation]:
        """
        获取随机动画组合
        :return: 一个随机动画组合
        """
        animations = AnimationLoader.load(self.animations, self.root_path)
        result: dict[str, Animation] = {}
        state: str
        anims: list[Animation]
        for state, anims in animations.items():
            result[state] = random.choice(anims)
        return result

    def get_id(self) -> str:
        return self.config_id
