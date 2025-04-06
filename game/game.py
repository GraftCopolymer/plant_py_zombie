import os
from ctypes import cast

import pygame

from base.scene import LevelScene, SceneManager
from game.character import Position
from game.character.character_config import ConfigManager, ZombieConfig
from game.character.zombie import ConfigZombie


class Game:
    zombie_path = 'resources/zombie'
    running = False
    delta: float = 0
    screen_size: tuple[int, int] = (1400, 600)

    @staticmethod
    def run():
        pygame.init()
        Game.running = True

        screen = pygame.display.set_mode(Game.screen_size)
        clock = pygame.time.Clock()
        # 加载资源文件
        # 加载所有僵尸
        print(os.path.abspath(Game.zombie_path))
        for directory in os.listdir(Game.zombie_path):
            directory_path = os.path.join(Game.zombie_path, directory)
            all_items = os.listdir(directory_path)
            files = [item for item in all_items if os.path.isfile(os.path.join(directory_path, item))]
            target_name = "{}.json".format(directory)
            json_path = os.path.join(directory_path, target_name)
            if target_name not in files: continue
            ConfigManager().load('zombie', json_path)

        scene_manager = SceneManager()
        test_level = LevelScene(pygame.image.load('./resources/scene/first_day/map0.jpg'), "first_day", scene_manager)
        test_config_zombie = ConfigZombie(ConfigManager().get_zombie_config('normal_zombie'), test_level)
        test_config_zombie.set_position(Position(700, 300))
        test_config_zombie.attack()

        while Game.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    Game.running = False

            pygame.display.flip()
            scene_manager.update(Game.delta)
            scene_manager.draw(screen)

            Game.delta = clock.tick(60)

        pygame.quit()