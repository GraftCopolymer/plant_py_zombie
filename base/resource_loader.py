import os
import threading

import pygame.image
from pygame import Surface
from pygame_gui import UIManager

from game.character.character_config import CharacterConfigManager


class ResourceLoader:
    """
    资源加载器，单例
    """
    _instance = None
    _lock = threading.Lock()
    _bullets: dict[str, Surface] = {}
    _particles: dict[str, Surface] = {}
    _themes: list[str] = []

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def load_zombie(self, zombie_path: str) -> None:
        """
        加载僵尸资源
        :return: None
        """
        for directory in os.listdir(zombie_path):
            directory_path = os.path.join(zombie_path, directory)
            if not os.path.isdir(directory_path):
                continue  # 跳过非目录

            target_name = "{}.json".format(directory)
            json_path = os.path.join(directory_path, target_name)

            if not os.path.isfile(json_path):
                continue  # 跳过不包含对应文件夹名称的json文件的文件夹

            CharacterConfigManager().load('zombie', json_path)

    def load_bullet(self, bullet_path: str):
        """
        加载所有子弹
        """
        for bullet_dir in os.listdir(bullet_path):
            b_d = os.path.join(bullet_path, bullet_dir)
            if not os.path.isdir(b_d): continue
            images = os.listdir(b_d)
            # 加载遇到的第一张图
            self._bullets[bullet_dir] = pygame.image.load(os.path.join(b_d, images[0])).convert_alpha()

    def load_particles(self, particle_path: str):
        """
        加载粒子效果
        :param particle_path: 粒子效果路径
        """
        for particle_dir in os.listdir(particle_path):
            p_d = os.path.join(particle_path, particle_dir)
            if not os.path.isdir(p_d): continue
            images = os.listdir(p_d)
            # 加载遇到的第一张图
            self._particles[particle_dir] = pygame.image.load(os.path.join(p_d, images[0])).convert_alpha()

    def load_plant_animation(self, plant_animation_path: str):
        for directory in os.listdir(plant_animation_path):
            directory_path = os.path.join(plant_animation_path, directory)
            if not os.path.isdir(directory_path):
                continue  # 跳过非目录

            target_name = "{}.json".format(directory)
            json_path = os.path.join(directory_path, target_name)

            if not os.path.isfile(json_path):
                continue  # 跳过不包含对应文件夹名称的json文件的文件夹

            CharacterConfigManager().load('animation', json_path)

    def load_theme_to_manager(self, theme_path: str, ui_manager: UIManager) -> None:
        # 加载全局主题文件
        theme_file = os.path.join(theme_path, 'theme.json')
        ui_manager.get_theme().load_theme(theme_file)
        # 加载各组件主题文件
        for directory in os.listdir(theme_path):
            directory_path = os.path.join(theme_path, directory)
            if not os.path.isdir(directory_path):
                continue  # 跳过非目录

            target_name = "{}.json".format(directory)
            json_path = os.path.join(directory_path, target_name)

            if not os.path.isfile(json_path):
                continue  # 跳过不包含对应文件夹名称的json文件的文件夹

            self._themes.append(json_path)
            ui_manager.get_theme().load_theme(json_path)
            print(f'已加载主题文件: {json_path}')

    def get_bullet_image(self, bullet_name: str) -> Surface:
        return self._bullets[bullet_name]

    def load_plant(self) -> None:
        """
        加载植物 TODO
        :return: None
        """
        pass
