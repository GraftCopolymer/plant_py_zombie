import abc
import math
from abc import abstractmethod
from typing import Union, TYPE_CHECKING

import pygame.sprite
from pygame import Surface

from base.animation import StatefulAnimation
from base.config import LAYERS
from base.game_grid import AbstractPlantCell, GrassPlantCell, WaterPlantCell
from base.sprite.game_sprite import GameSprite
from game.character.bullets import Bullet
from game.character.character_config import CharacterConfigManager
from game.character.plant_ability import Shooter
from game.level.state_machine import StateMachine, State
from game.level.plant_creator import PlantCreator

if TYPE_CHECKING:
    from game.level.level_scene import LevelScene

class PlantStateMachine(StateMachine):
    """
    植物状态机
    """
    def __init__(self):
        super().__init__()
        # 处于攻击冷却状态
        self.in_interval = State('in_interval')
        self.attack = State('attack')
        # 受击状态
        self.hurt = State('hurt')
        self.add_state(self.in_interval, {'attack', 'hurt'})
        self.add_state(self.attack, {'in_interval', 'hurt'})
        self.add_state(self.hurt, {'attack', 'in_interval'})


class AbstractPlant(GameSprite, abc.ABC):
    # 种植需消耗的阳光, 所有对象共享
    sun_cost = 0
    # 种植冷却, 所有对象共享, 单位ms
    plant_cold_down = 0

    def __init__(self, max_health: float, *args, **kwargs):
        super().__init__([], None, z=LAYERS['plant0'])
        self.cell: Union[AbstractPlantCell, None] = None
        # 最大生命值
        self.max_health = max_health
        # 当前生命值
        self.health = self.max_health
        self.hurt_state = False
        self.animation: StatefulAnimation = self.load_animation(*args, **kwargs)
        self.animator: Union[PlantAnimator, None] = None
        self.hit_flash_timer = 0
        self.hit_flash_time = 100
        self.hit_flash_intensity = 50
        self.image = self.animation.get_current_image()
        self.preview_image = self.image.copy()
        self.preview_image.set_alpha(100)
        self.level: Union['LevelScene', None] = None
        self.image_scale = 1.0

    def set_cell(self, cell: AbstractPlantCell):
        self.cell = cell

    def update(self, dt: float) -> None:
        super().update(dt)
        self.animation.update(dt)
        self.image = self.animation.get_current_image()
        if self.animator is not None:
            self.animator.update(dt)


    def setup_sprite(self, group: pygame.sprite.Group, cell: AbstractPlantCell, level: 'LevelScene'):
        """
        设定植物信息
        :param group: 精灵组
        :param cell: 所在单元格
        :param level: 所在关卡场景
        """
        super().setup_sprite()
        self.group = group
        self.cell = cell
        self.rect = self.image.get_rect()
        self.rect.center = self.cell.rect.center
        self.world_pos = pygame.Vector2(self.rect.topleft)
        self.level = level

    def get_preview_image(self) -> Surface:
        """
        :return: 植物预览图，用于在种植前跟踪显示在鼠标上的半透明图
        """
        return self.preview_image

    def hurt(self, source, damage: float) -> None:
        self.health -= damage
        self.hurt_state = True
        self.hit_flash_timer = 0

    def hit_flash(self, dt: float):
        """
        受击时播放白色闪光
        """
        alpha = int(100 * max(1 - self.hit_flash_timer / self.hit_flash_time, 0))
        self.hit_flash_timer += dt
        if self.hit_flash_timer >= self.hit_flash_time:
            self.hit_flash_timer = 0
            self.hurt_state = False
        white_mask = Surface(self.image.get_size()).convert_alpha()
        white_mask.fill((self.hit_flash_intensity, self.hit_flash_intensity, self.hit_flash_intensity, alpha))
        self.image.blit(white_mask, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    @abstractmethod
    def load_animation(self, *args, **kwargs) -> StatefulAnimation: pass

class GrassPlant(AbstractPlant, abc.ABC):
    def __init__(self, max_health, *args, **kwargs):
        AbstractPlant.__init__(self, max_health, *args, **kwargs)

    def setup_sprite(self, group: pygame.sprite.Group, cell: GrassPlantCell, level: 'LevelScene'):
        super().setup_sprite(group, cell, level)

class WaterPlant(AbstractPlant, abc.ABC):
    def __init__(self, max_health, *args, **kwargs):
        AbstractPlant.__init__(self, max_health, *args, **kwargs)

    def setup_sprite(self, group: pygame.sprite.Group, cell: WaterPlantCell, level: 'LevelScene'):
        super().setup_sprite(group, cell, level)

class GrassShooterPlant(GrassPlant, Shooter, abc.ABC):
    def __init__(self, max_health: float, shoot_interval: float=1000):
        super().__init__(max_health)
        # 发射冷却时间(ms)
        self.shoot_interval = shoot_interval
        self.shoot_timer = 0
        self.animator = VerticalBruhPlantAnimator(self)

    @abstractmethod
    def load_animation(self) -> StatefulAnimation: pass

    from game.character.bullets import Bullet
    @abstractmethod
    def get_bullet(self) -> Bullet: pass

    @abstractmethod
    def should_shoot(self) -> bool: pass

    @abstractmethod
    def get_range(self) -> float:
        return 1000

    def shoot(self) -> None:
        self.animator.start()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.animator.update(dt)

    def test_zombie_in_row(self) -> bool:
        # 检测当前行是否有僵尸, 且僵尸需在植物的右边
        zombies = self.level.get_zombies()
        for z in zombies:
            if z.row == self.cell.row and self.get_center_pos().x < z.get_center_pos().x and z.is_alive():
                return True
        return False

@PlantCreator.register_plant('pea_shooter')
class PeaShooter(GrassShooterPlant):
    """
    豌豆射手
    """
    sun_cost = 100
    plant_cold_down = 10000
    def __init__(self):
        super().__init__(200, shoot_interval=1500)

    def load_animation(self) -> StatefulAnimation:
        config = CharacterConfigManager().get_animation_config("pea_shooter_animation")
        animation = StatefulAnimation(config.get_random_animation_group(), config.init_state)
        return animation

    def get_range(self) -> float:
        return 1000

    def should_shoot(self) -> bool:
        # 处于冷却时间直接返回False
        if self.shoot_timer < self.shoot_interval: return False
        return self.test_zombie_in_row()

    def shoot(self) -> None:
        super().shoot()
        bullet = self.get_bullet()
        # 将子弹挂载到场景中
        bullet.setup_sprite(self.group, self, self.level)

    from game.character.bullets import Bullet
    def get_bullet(self) -> Bullet:
        from game.character.bullets import PeaBullet
        return PeaBullet()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.shoot_timer += dt
        if self.should_shoot():
            self.shoot()
            # 重置发射冷却
            self.shoot_timer = 0

@PlantCreator.register_plant('machine_gun_shooter')
class MachineGunShooter(GrassShooterPlant):
    """
    机枪射手
    """
    sun_cost = 200
    plant_cold_down = 10000
    def __init__(self):
        super().__init__(200, shoot_interval=1200)
        # 一次连发中每颗豆子间的时间间隔
        self.micro_interval = 150
        self.micro_timer = 0
        # 每轮发射的豆子数量
        self.pea_number_per_turn = 4
        self.pea_counter = 0
        # 须保证每个豆子连发的间隔总和不大于每轮连发之间的时间间隔
        assert 3 * self.pea_number_per_turn <= self.shoot_interval

    def load_animation(self) -> StatefulAnimation:
        config = CharacterConfigManager().get_animation_config("machine_gun_shooter_animation")
        animation = StatefulAnimation(config.get_random_animation_group(), config.init_state)
        return animation

    def should_shoot(self) -> bool:
        if self.shoot_timer < self.shoot_interval: return False
        if self.micro_timer < self.micro_interval or self.pea_counter == self.pea_number_per_turn: return False

        return self.test_zombie_in_row()

    def shoot(self) -> None:
        super().shoot()
        from game.character.bullets import PeaBullet
        bullet = PeaBullet()
        bullet.setup_sprite(self.group, self, self.level)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.shoot_timer += dt
        self.micro_timer += dt
        if self.should_shoot():
            self.shoot()
            self.pea_counter += 1
            self.micro_timer = 0
        if self.pea_counter == self.pea_number_per_turn or not self.test_zombie_in_row():
            self.shoot_timer = 0
            self.pea_counter = 0

    def get_range(self) -> float:
        return 1000

    from game.character.bullets import Bullet
    def get_bullet(self) -> Bullet:
        from game.character.bullets import PeaBullet
        return PeaBullet()

@PlantCreator.register_plant('iced_pea_shooter')
class IcedPeaShooter(GrassShooterPlant):
    """
    寒冰射手
    """
    sun_cost = 175
    plant_cold_down = 15000
    def __init__(self):
        super().__init__(200, shoot_interval=1000)

    def load_animation(self) -> StatefulAnimation:
        config = CharacterConfigManager().get_animation_config("iced_pea_shooter_animation")
        animation = StatefulAnimation(config.get_random_animation_group(), config.init_state)
        return animation

    def get_bullet(self) -> Bullet:
        from game.character.bullets import IcedPeaBullet
        return IcedPeaBullet()

    def should_shoot(self) -> bool:
        # 处于冷却时间直接返回False
        if self.shoot_timer < self.shoot_interval: return False
        return self.test_zombie_in_row()

    def shoot(self) -> None:
        super().shoot()
        bullet = self.get_bullet()
        bullet.setup_sprite(self.group, self, self.level)

    def get_range(self) -> float:
        return 1000

    def update(self, dt: float) -> None:
        super().update(dt)
        self.shoot_timer += dt
        if self.should_shoot():
            self.shoot()
            # 重置发射冷却
            self.shoot_timer = 0


class PlantAnimator(abc.ABC):
    """
    植物非帧动画
    """
    def __init__(self, target: AbstractPlant, duration=200):
        self.target = target
        self.timer = 0
        self.duration = duration
        self.running = False

    def start(self):
        self.timer = 0
        self.running = True

    @abstractmethod
    def update(self, dt: float): pass


class VerticalBruhPlantAnimator(PlantAnimator):
    def __init__(self, plant: AbstractPlant, duration=200):
        super().__init__(plant, duration)
        self.scale_y: float = 1.0

    def update(self, dt: float):
        original_image = self.target.image

        # 缩放图像
        scaled_size = (int(original_image.get_width() * 1),
                       int(original_image.get_height() * self.scale_y))
        self.target.image = pygame.transform.scale(original_image, scaled_size)

        # 重新定位，保持底部不变
        self.target.rect = self.target.image.get_rect(midbottom=self.target.rect.midbottom)
        self.target.world_pos = pygame.Vector2(self.target.rect.topleft)
        if not self.running:
            return

        self.timer += dt
        t = min(self.timer / self.duration, 1)

        # 弹性缩放曲线
        scale = 1 + 0.08 * math.sin(math.pi + t * math.pi)
        self.scale_y = scale

        if t >= 1:
            self.running = False
            self.scale_y = 1.0