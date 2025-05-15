import random

import pygame
import pygame_gui
from pygame import Clock, Surface

from base.cameragroup import CameraAnimator, EaseInOutQuad
from base.game_event import EventBus, ButtonClickEvent, StartPlantEvent, WillGenZombieEvent
from base.resource_loader import ResourceLoader
from base.scene import SceneManager
from base.sprite.game_sprite import GameSprite
from game.character.character_config import CharacterConfigManager
from game.character.plant import PeaShooter, MachineGunShooter, IcedPeaShooter
from game.character.zombie import ConfigZombie, ZombieStateMachine
from game.level.level_scene import LevelScene


def on_start_plant(event: ButtonClickEvent):
    if "#start_plant_button" in event.ui_element.object_ids:
        EventBus().publish(StartPlantEvent(PeaShooter()))

def on_start_plant_machine_gun(event: ButtonClickEvent):
    if "#start_plant_machine_gun_button" in event.ui_element.object_ids:
        EventBus().publish(StartPlantEvent(MachineGunShooter()))

def on_start_plant_iced_pea_shooter(event: ButtonClickEvent):
    if "#start_plant_iced_pea_shooter_button" in event.ui_element.object_ids:
        EventBus().publish(StartPlantEvent(IcedPeaShooter()))

def on_gen_zombie(event: ButtonClickEvent):
    if '#zombie_gen_button' in event.ui_element.object_ids:
        for _ in range(1):
            zombie = ConfigZombie(CharacterConfigManager().get_zombie_config('normal_zombie'), ZombieStateMachine(),[])
            position = pygame.Vector2(1000, random.randint(50, Game.screen_size[1] - 50))
            zombie.set_position(position)
            zombie.walk()
            row = random.randint(0, 4)
            EventBus().publish(WillGenZombieEvent(zombie, row))

def on_next_level(event: ButtonClickEvent):
    if '#next_level_button' in event.ui_element.object_ids:
        SceneManager().push_scene(LevelScene('./resources/level/first_day/first_day.tmx', "second_day"))

class Game:
    zombie_path = 'resources/zombie'
    bullet_path = 'resources/bullet'
    particle_path = 'resources/particle'
    plant_animation_path = "resources/plant"
    theme_path = 'resources/ui'
    running = False
    delta: float = 0
    screen_size: tuple[int, int] = (900, 600)
    # 子弹有效范围，超出该范围将删除子弹
    bullets_exist_rect: pygame.Rect = pygame.Rect(-100, -100, screen_size[0] + 200, screen_size[1] + 200)
    clock: Clock = None
    screen: Surface = None
    debug_mode: bool = False

    @staticmethod
    def end():
        Game.running = False

    @staticmethod
    def init():
        # 加载UI
        Game.ui_manager = pygame_gui.UIManager(Game.screen_size, starting_language='zh')
        # 加载游戏屏幕
        Game.screen = pygame.display.set_mode(Game.screen_size)
        pygame.display.set_caption('Plants py. Zombies')
        # 加载游戏时钟
        Game.clock = pygame.time.Clock()
        # 加载资源文件
        # 加载所有僵尸
        ResourceLoader().load_zombie(Game.zombie_path)
        # 加载所有子弹
        ResourceLoader().load_bullet(Game.bullet_path)
        # 加载所有粒子效果
        ResourceLoader().load_particles(Game.particle_path)
        # 加载所有动画
        ResourceLoader().load_plant_animation(Game.plant_animation_path)
        # 加载UI主题
        ResourceLoader().load_theme_to_manager(Game.theme_path, Game.ui_manager)

    @staticmethod
    def bullet_in_screen(sprite: GameSprite) -> bool:
        return Game.bullets_exist_rect.colliderect(sprite.rect)

    @staticmethod
    def run():
        pygame.init()
        Game.init()
        Game.running = True

        scene_manager = SceneManager()

        camera_pos = pygame.Vector2(0,0)

        # EventBus().subscribe_ui(ButtonClickEvent, on_start_plant)
        # EventBus().subscribe_ui(ButtonClickEvent, on_gen_zombie)
        # EventBus().subscribe_ui(ButtonClickEvent, on_start_plant_machine_gun)
        # EventBus().subscribe_ui(ButtonClickEvent, on_start_plant_iced_pea_shooter)
        # EventBus().subscribe_ui(ButtonClickEvent, on_next_level)

        from game.ui.main_menu_scene import MainMenuScene
        main_menu = MainMenuScene()
        scene_manager.push_scene(main_menu)

        while Game.running:
            EventBus().process_event()

            pygame.display.flip()
            scene_manager.update(Game.delta)
            scene_manager.draw(Game.screen)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                camera_pos.y -= Game.delta * 1
            if keys[pygame.K_s]:
                camera_pos.y += Game.delta * 1
            if keys[pygame.K_a]:
                camera_pos.x -= Game.delta * 1
            if keys[pygame.K_d]:
                camera_pos.x += Game.delta * 1

            Game.delta = Game.clock.tick(60)

        pygame.quit()