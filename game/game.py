import pygame

from base.cameragroup import CameraAnimator, EaseInOutQuad
from base.config import LAYERS
from base.resource_manager import ResourceLoader
from base.scene import LevelScene, SceneManager
from game.character import Position
from game.character.character_config import ConfigManager
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
        ResourceLoader().load_zombie(Game.zombie_path)

        scene_manager = SceneManager()
        # 测试游戏场景和僵尸
        test_level = LevelScene(pygame.image.load('./resources/scene/first_day/map0.jpg'), "first_day", scene_manager)
        test_config_zombie = ConfigZombie(ConfigManager().get_zombie_config('normal_zombie'), test_level.get_group())
        test_config_zombie.set_position(Position(700, 300))
        test_config_zombie.z = LAYERS['zombie0']
        test_config_zombie.attack()
        test_level.camera.animator = CameraAnimator(test_level.camera, 200, EaseInOutQuad())

        camera_pos = pygame.Vector2(0,0)

        while Game.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    Game.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        test_level.camera.animate_to(test_level.camera.offset + pygame.Vector2(200, 0))
                    if event.key == pygame.K_n:
                        test_level.camera.animate_to(test_level.camera.offset - pygame.Vector2(200, 0))

            pygame.display.flip()
            scene_manager.update(Game.delta)
            scene_manager.draw(screen)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                camera_pos.y -= Game.delta * 1
            if keys[pygame.K_s]:
                camera_pos.y += Game.delta * 1
            if keys[pygame.K_a]:
                camera_pos.x -= Game.delta * 1
            if keys[pygame.K_d]:
                camera_pos.x += Game.delta * 1


            Game.delta = clock.tick(60)

        pygame.quit()