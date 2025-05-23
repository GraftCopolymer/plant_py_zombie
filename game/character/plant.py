import abc
import math
import random
from abc import abstractmethod
from typing import Union, TYPE_CHECKING

import pygame.sprite
from pygame import Surface, Vector2

from base.animation import StatefulAnimation, OncePlayController
from base.config import LAYERS
from base.game_grid import AbstractPlantCell, GrassPlantCell, WaterPlantCell
from base.sprite.game_sprite import GameSprite
from game.character.bullets import Bullet, JalapenoFire
from game.character.character_config import ConfigManager
from game.character.plant_ability import Shooter, TimingAction, StatefulPlant
from game.character.plant_state_machine import AbstractPlantStateMachine, WallnutStateMachine, SunShroomStateMachine, \
    CherryBombStateMachine, JalapenoStateMachine
from game.character.zombie import AbstractZombie
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
        super().__init__([], None, z=LAYERS['plant1'])
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
        self.image_offset = self.animation.get_current_animation().offset
        self.image = self.animation.get_current_image()
        if self.animator is not None:
            self.animator.update(dt)
        if self.hurt_state:
            self.hit_flash(dt)


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
        self.level.add_plant(self)

    def get_preview_image(self) -> Surface:
        """
        :return: 植物预览图，用于在种植前跟踪显示在鼠标上的半透明图
        """
        return self.preview_image

    def hurt(self, source, damage: float) -> None:
        self.health -= damage
        if not self.is_alive():
            self.level.remove_plant(self)
            return
        self.hurt_state = True
        self.hit_flash_timer = 0

    def can_be_eaten(self):
        """
        当前是否能被吃, 默认可以被吃，子类可以自己实现逻辑，例如地刺无法被吃
        """
        return True

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

    def is_alive(self):
        """
        当前植物是否还活着(未被销毁)
        """
        return self.health > 0

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

class InstantUsedPlant(GrassPlant, StatefulPlant, abc.ABC):
    def __init__(self, max_health: int):
        # 建议设置一个较大的生命值，以免在使用前死亡
        super().__init__(max_health=max_health)

    def update(self, dt: float) -> None:
        super().update(dt)
        controller = self.animation.get_current_controller()
        if isinstance(controller, OncePlayController):
            if self.get_state_machine().get_state() == self.get_used_state() and controller.over:
                # 使用完毕，删除植物
                self.level.remove_plant(self)
            elif self.get_state_machine().can_transition_to(self.get_used_state()) and controller.over:
                # 使用
                self.use()
        else:
            raise ValueError('InstantUsePlant的所有动画都应该是一次性的!')
        self.handle_state(dt)

    @abstractmethod
    def use(self):
        pass

    @abstractmethod
    def load_animation(self, *args, **kwargs) -> StatefulAnimation:
        pass

    def can_be_eaten(self):
        if self.get_state_machine().get_state() == self.get_used_state():
            return False
        return True

    @abstractmethod
    def get_state_machine(self) -> AbstractPlantStateMachine:
        pass

    @abstractmethod
    def get_ready_to_use_state(self) -> str:
        pass

    @abstractmethod
    def get_used_state(self) -> str:
        pass

    def handle_state(self, *args, **kwargs) -> None:
        pass

    def hurt(self, source, damage: float) -> None:
        # 使用后不再受伤害
        if self.get_state_machine().get_state() == self.get_used_state():
            return
        super().hurt(source, damage)

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
        config = ConfigManager().get_animation_config("pea_shooter_animation")
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
        config = ConfigManager().get_animation_config("machine_gun_shooter_animation")
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
        config = ConfigManager().get_animation_config("iced_pea_shooter_animation")
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

@PlantCreator.register_plant('sun_flower')
class SunFlower(GrassPlant, TimingAction):
    # 种植需消耗的阳光, 所有对象共享
    sun_cost = 50
    # 种植冷却, 所有对象共享, 单位ms
    plant_cold_down = 10000
    # 最小阳光生成间隔
    min_sun_produce_interval = 7000
    # 最大阳光生成间隔
    max_sun_produce_interval = 10000
    def __init__(self):
        super().__init__(max_health=150)
        # 产生阳光冷却计时器, 单位ms
        self.produce_timer = 0
        self.current_action_interval = self.getNextActionInterval()

    def load_animation(self) -> StatefulAnimation:
        config = ConfigManager().get_animation_config("sun_flower_animation")
        animation = StatefulAnimation(config.get_random_animation_group(), config.init_state)
        return animation

    def getNextActionInterval(self) -> int:
        return random.randint(SunFlower.min_sun_produce_interval, SunFlower.max_sun_produce_interval)

    def doAction(self) -> None:
        # 在本植物坐标处生成阳光
        from game.level.sun import Sun
        spawn_pos = self.world_pos.copy()
        # 在距离生成处的位置随机生成一个任意方向的变量作为阳光的目的地
        des_direct = Vector2(random.uniform(-1, 1), random.uniform(-1,1)).normalize()
        des_distance = 30
        sun = Sun(self.level.camera, spawn_pos, spawn_pos + des_direct * des_distance)
        sun.value = 25
        sun.setup_sprite(self.level, revise=False)

    def update(self, dt: float) -> None:
        super().update(dt)
        if hasattr(self.level, 'is_night') and self.level.is_night:
            # 向日葵在夜晚无法生成阳光
            return
        self.produce_timer += dt
        if self.produce_timer >= self.current_action_interval:
            self.produce_timer = 0
            self.current_action_interval = self.getNextActionInterval()
            # 生成阳光
            self.doAction()

@PlantCreator.register_plant('wallnut')
class Wallnut(GrassPlant, StatefulPlant):
    """
    坚果墙
    """
    plant_cold_down = 20000
    sun_cost = 50
    def __init__(self):
        super().__init__(max_health=4000)
        self.state_machine = WallnutStateMachine()

    def load_animation(self) -> StatefulAnimation:
        config = ConfigManager().get_animation_config("wallnut_animation")
        animation = StatefulAnimation(config.get_random_animation_group(), config.init_state)
        return animation

    def update(self, dt: float) -> None:
        super().update(dt)
        self.handle_state(dt)

    def cracked1(self):
        self.get_state_machine().transition_to('cracked1')
        self.animation.change_state('cracked1')

    def cracked2(self):
        self.get_state_machine().transition_to('cracked2')
        self.animation.change_state('cracked2')

    def get_state_machine(self) -> AbstractPlantStateMachine:
        return self.state_machine

    def handle_state(self, dt: float) -> None:
        if self.health <= self.max_health * 2/3 and self.get_state_machine().can_transition_to('cracked1'):
            self.cracked1()
        elif self.health <= self.max_health * 1/3 and self.get_state_machine().can_transition_to('cracked2'):
            self.cracked2()

@PlantCreator.register_plant('sun_shroom')
class SunShroom(GrassPlant, StatefulPlant, TimingAction):
    """
    阳光菇
    """
    sun_cost = 25
    plant_cold_down = 7000
    # 最小阳光生成间隔
    min_sun_produce_interval = 6000
    # 最大阳光生成间隔
    max_sun_produce_interval = 10000
    # 生长时间
    grow_time = 40000
    def __init__(self):
        super().__init__(max_health=100)
        self.state_machine = SunShroomStateMachine()
        self.grow_timer = 0
        self.sun_produce_timer = 0
        self.sun_produce_interval = self.getNextActionInterval()

    def update(self, dt: float) -> None:
        super().update(dt)
        if not hasattr(self.level, 'is_night') and self.get_state_machine().can_transition_to('sleep'):
            # 白天直接睡觉
            self.get_state_machine().transition_to('sleep')
            self.animation.change_state(self.get_state_machine().get_state())

        self.sun_produce_timer += dt
        if self.sun_produce_timer >= self.sun_produce_interval:
            self.sun_produce_timer = 0
            self.sun_produce_interval = self.getNextActionInterval()
            # 产生阳光
            self.doAction()
        self.handle_state(dt)

    def load_animation(self, *args, **kwargs) -> StatefulAnimation:
        config = ConfigManager().get_animation_config('sun_shroom_animation')
        return StatefulAnimation(config.get_random_animation_group(), config.init_state)

    def grow(self):
        """
        生长至成年状态
        """
        self.state_machine.transition_to('big_idle')
        self.animation.change_state(self.state_machine.get_state())

    def is_sleeping(self):
        return self.get_state_machine().get_state() == 'sleep'

    def get_state_machine(self) -> AbstractPlantStateMachine:
        return self.state_machine

    def handle_state(self, dt: float) -> None:
        if self.state_machine.get_state() == 'small_idle':
            self.grow_timer += dt
            if self.grow_timer >= SunShroom.grow_time and self.state_machine.can_transition_to('big_idle'):
                self.grow()
                self.grow_timer = 0

    def getNextActionInterval(self) -> int:
        return random.randint(SunShroom.min_sun_produce_interval, SunShroom.max_sun_produce_interval)

    def doAction(self) -> None:
        # 根据当前的生长状态生成阳光
        # 幼年时生成15阳光值的阳光，成年生成25阳光值阳光
        sun_value = 0
        if self.state_machine.get_state() == 'small_idle':
            sun_value = 15
        elif self.state_machine.get_state() == 'big_idle':
            sun_value = 25
        else:
            # 其他状态直接退出阳光生成
            return
        from game.level.sun import Sun
        spawn_pos = self.world_pos.copy()
        # 在距离生成处的位置随机生成一个任意方向的变量作为阳光的目的地
        des_direct = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
        des_distance = 30
        sun = Sun(self.level.camera, spawn_pos, spawn_pos + des_direct * des_distance)
        sun.value = sun_value
        sun.setup_sprite(self.level, revise=False)

@PlantCreator.register_plant('cherry_bomb')
class CherryBomb(InstantUsedPlant):
    """
    樱桃炸弹，爆炸前摇取决于动画长度，动画执行完毕后爆炸
    """
    sun_cost = 150
    plant_cold_down = 15000
    # 爆炸伤害
    damage = 999999

    def __init__(self):
        # 设置一个较大的生命值，以免在爆炸前死亡
        super().__init__(max_health=4000)
        self.state_machine = CherryBombStateMachine()

    def use(self):
        if self.get_state_machine().can_transition_to('boomed'):
            self.get_state_machine().transition_to('boomed')
            self.animation.change_state(self.get_state_machine().get_state())

            # 检测附近僵尸，检测形状为AABB矩形
            extend_rect = self.rect.copy().inflate(100, 100)
            for z in self.level.zombies:
                if extend_rect.colliderect(z.rect):
                    if hasattr(z, 'boom_dying') and callable(getattr(z, 'boom_dying')):
                        z.boom_dying()

    def get_ready_to_use_state(self) -> str:
        return 'ready_to_boom'

    def get_used_state(self) -> str:
        return 'boomed'

    def load_animation(self, *args, **kwargs) -> StatefulAnimation:
        config = ConfigManager().get_animation_config('cherry_bomb_animation')
        return StatefulAnimation(config.get_random_animation_group(), config.init_state)

    def get_state_machine(self) -> AbstractPlantStateMachine:
        return self.state_machine

@PlantCreator.register_plant('jalapeno')
class Jalapeno(InstantUsedPlant):
    """
    火爆辣椒
    """
    sun_cost = 125
    plant_cold_down = 10000
    def __init__(self):
        super().__init__(max_health=4000)
        self.state_machine = JalapenoStateMachine()

    def use(self):
        if self.get_state_machine().can_transition_to('fired'):
            self.get_state_machine().transition_to('fired')
            self.animation.change_state(self.get_state_machine().get_state())
            fire_bullet = JalapenoFire()
            fire_bullet.setup_sprite(self.level.camera, self, self.level)

            # 检测附近僵尸，检测形状为AABB矩形
            extend_rect = self.rect.copy().inflate(100, 100)
            for z in self.level.zombies:
                if extend_rect.colliderect(z.rect):
                    if hasattr(z, 'boom_dying') and callable(getattr(z, 'boom_dying')):
                        z.boom_dying()

    def load_animation(self, *args, **kwargs) -> StatefulAnimation:
        config = ConfigManager().get_animation_config('jalapeno_animation')
        return StatefulAnimation(config.get_random_animation_group(), config.init_state)

    def get_state_machine(self) -> AbstractPlantStateMachine:
        return self.state_machine

    def get_ready_to_use_state(self) -> str:
        return 'ready_to_fire'

    def get_used_state(self) -> str:
        return 'fired'


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