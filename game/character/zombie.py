from __future__ import annotations
import abc
import random
from abc import abstractmethod
from ctypes import cast
from typing import Union, TYPE_CHECKING

import pygame
from pygame import Surface, Vector2

from base.animation import StatefulAnimation, OncePlayController
from base.config import LAYERS
from base.game_grid import AbstractPlantCell
from base.sprite.game_sprite import GameSprite
from game.character import Position
from game.character.character_config import ZombieConfig, CharacterConfigManager
from game.level.state_machine import State, StateMachine
from game.level.zombie_creator import ZombieCreator

if TYPE_CHECKING:
    from game.level.level_scene import LevelScene


class AbstractZombieStateMachine(StateMachine, abc.ABC):
    def __init__(self):
        super().__init__()


class ZombieStateMachine(AbstractZombieStateMachine):
    def __init__(self):
        super().__init__()
        self.walk = State('walk')
        self.idle = State('idle')
        self.dying = State('dying')
        self.attack = State('attack')
        self.add_state(self.idle, {'walk'})
        self.add_state(self.walk, {'attack', 'dying'})
        self.add_state(self.dying, set())
        self.add_state(self.attack, {'dying', 'walk'})
        self.set_initial_state('walk')


class BucketheadZombieStateMachine(ZombieStateMachine):
    def __init__(self):
        super().__init__()
        # 顶着完整头盔走
        self.walk_with_bucket = State('walk_with_bucket')
        # 顶着破头盔走
        self.walk_with_broken_bucket = State('walk_with_broken_bucket')
        # 注意，无头盔行走使用状态walk(父类中定义)
        self.add_state(self.walk_with_bucket, {'walk', 'walk_with_broken_bucket', 'attack', 'dying'})
        self.add_state(self.walk_with_broken_bucket, {'walk', 'attack', 'dying'})
        self.set_initial_state('walk_with_bucket')


class AbstractZombie(GameSprite, abc.ABC):
    def __init__(self,
                 group: Union[pygame.sprite.Group, list],
                 max_health: float,
                 animation: StatefulAnimation,
                 speed: float,
                 state_machine: AbstractZombieStateMachine,
                 position: Position = pygame.math.Vector2((0, 0)),
                 zombie_offset: pygame.Vector2 = pygame.Vector2(0, 20)):
        GameSprite.__init__(self, group, animation.get_current_image(), position)
        self.speed_factor = 1.0
        self._origin_speed = speed
        self.speed = self._origin_speed
        self.animation = animation
        self.max_health = max_health
        self.health = self.max_health
        self.state_machine: AbstractZombieStateMachine = state_machine
        self.animation.change_state(self.get_state())
        # 僵尸所在的关卡的行列数（从0开始）
        self.row = 0
        # 越在下层的僵尸图层越高
        self.z = LAYERS[f'zombie{self.row}']
        self.level: Union['LevelScene', None] = None
        # 僵尸锚点偏移，用于定位僵尸在单元格内的行走纵坐标相对于单元格中央的偏移
        self.zombie_offset = zombie_offset
        # 冰冻时长, 修改该属性请使用self.set_iced_remain_time方法,单位ms
        self.iced_remain_time = 0

    def update(self, dt: float) -> None:
        GameSprite.update(self, dt)
        self.set_iced_remain_time(self.iced_remain_time - dt)
        self.speed = self._origin_speed * self.speed_factor
        self.animation.update(dt)
        self.image_offset = self.animation.get_current_animation().offset
        self.image = self.animation.get_current_image()
        self.rect = self.image.get_bounding_rect()
        self.move_rect_to(self.world_pos)

    def get_state(self) -> str:
        return self.state_machine.get_state()

    def setup_sprite(self, group: pygame.sprite.Group, level: 'LevelScene', row: int = 0,
                     move_to_row: bool = False) -> None:
        self.group = group
        self.level = level
        self.change_row(row)

    def get_offset_center_position(self) -> pygame.Vector2:
        return self.get_center_pos() + self.zombie_offset

    def change_row(self, new_row) -> None:
        self.row = new_row
        # 更改其图层
        self.z = LAYERS[f'zombie{self.row}']

    def is_alive(self) -> bool:
        return self.health > 0

    def set_iced_remain_time(self, remain: float) -> None:
        """
        设置该僵尸的冰冻时间, 若传入的冰冻时间少于当前时间，则不进行更新
        :param remain: 剩余冰冻时间, 单位ms
        """
        if remain <= self.iced_remain_time: return
        self.iced_remain_time = max(remain, 0)

    def set_speed(self, speed: float) -> None:
        self.speed = speed

    def get_speed(self) -> float:
        return self.speed

    def get_original_speed(self) -> float:
        return self._origin_speed

    def set_speed_factor(self, factor: float):
        self.speed_factor = factor

    def debug_draw(self, surface: Surface, camera_pos: Vector2) -> None:
        pygame.draw.line(surface, 'red', self.get_offset_center_position() - camera_pos,
                         self.get_offset_center_position() + self.direction * 40 - camera_pos, 2)
        rect = self.rect.copy()
        rect.topleft -= camera_pos
        pygame.draw.rect(surface, 'red', rect, 2)
        pygame.draw.line(surface, 'blue', pygame.Vector2(0, 0), self.world_pos - camera_pos, 2)
        # 血量显示
        font = pygame.font.Font(None, 20)
        hp_text = font.render(f'{self.health}/{self.max_health}', True, 'yellow')
        surface.blit(hp_text, self.world_pos - camera_pos)

    @abstractmethod
    def hurt(self, source, damage: float):
        """
        由伤害者调用该方法
        :param source: 伤害源
        :param damage: 伤害值
        """
        pass

    @abstractmethod
    def move(self, dt: float) -> None: pass


class GenericZombie(AbstractZombie):
    """
    通用僵尸类
    提供生命值，idle、walk、attack、dying行为
    如需更多行为，请继承该类进行扩展
    """

    def __init__(self,
                 group: Union[pygame.sprite.Group, list],
                 health: float,
                 animation: StatefulAnimation,
                 state_machine: AbstractZombieStateMachine,
                 speed: float,
                 zombie_offset=pygame.Vector2(0, 20)):
        AbstractZombie.__init__(self, group, health, animation, speed, state_machine,
                                zombie_offset=zombie_offset)
        self.speed = speed
        # 僵尸位置
        self.rect = animation.get_current_image().get_bounding_rect()
        self.move_rect_to(self.world_pos)
        # 行走方向
        self.direction = pygame.math.Vector2([-1, 0])
        # 死亡时播放的渐隐动画时长（ms）
        self.died_fading_time = 2000
        # 渐隐动画计时器
        self.fading_timer = 0
        # 受击动画长度
        self.hit_flash_time = 100
        # 受击动画计时器
        self.hit_flash_timer = 0
        # 是否处于受击状态
        self.hurt_state: bool = False
        # 受击时白色闪光的强度(0 ~ 255之间)
        self.hit_flash_intensity = 50
        # 路径规划器
        self.path_finder: Union[ZombiePathFinder, None] = None
        # 冰冻速度乘因子，默认为1
        self.iced_speed_factor = 1

    def move(self, dt: float) -> None:
        super().move(dt)
        horizontal_dis = dt / 1000 * self.speed * self.direction
        self.set_position(self.world_pos + horizontal_dis)

    def attack(self):
        # 播放攻击动画
        self.state_machine.transition_to('attack')
        self.animation.change_state(self.get_state())

    def walk(self):
        self.state_machine.transition_to('walk')
        self.animation.change_state(self.get_state())

    def idle(self):
        self.state_machine.transition_to('idle')
        self.animation.change_state(self.get_state())

    def dying(self):
        self.state_machine.transition_to('dying')
        self.animation.change_state(self.get_state())

    def fading(self, dt: float):
        alpha = int(255 * max(1 - self.fading_timer / self.died_fading_time, 0))
        self.image.set_alpha(alpha)
        self.fading_timer += dt
        if self.fading_timer >= self.died_fading_time:
            self.level.remove_zombie(self)
            self.fading_timer = 0
            print("已清除僵尸")

    def hurt(self, source, damage: float):
        self.health -= damage
        self.hurt_state = True
        self.hit_flash_timer = 0

    def freeze(self) -> None:
        # 增加蓝色遮罩
        blue_mask = Surface(self.image.get_size())
        blue_mask.fill((168, 0, 0, 0))
        self.image.blit(blue_mask, (0,0), special_flags=pygame.BLEND_RGB_SUB)

    def hit_flash(self, dt: float):
        alpha = int(100 * max(1 - self.hit_flash_timer / self.hit_flash_time, 0))
        self.hit_flash_timer += dt
        if self.hit_flash_timer >= self.hit_flash_time:
            self.hit_flash_timer = 0
            self.hurt_state = False
        white_mask = Surface(self.image.get_size()).convert_alpha()
        white_mask.fill((self.hit_flash_intensity, self.hit_flash_intensity, self.hit_flash_intensity, alpha))
        self.image.blit(white_mask, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def setup_sprite(self, group: pygame.sprite.Group, level: 'LevelScene', row: int = 0,
                     move_to_row: bool = False) -> None:
        super().setup_sprite(group, level, row, move_to_row)
        self.path_finder = ZombiePathFinder(self)

    def update(self, dt: float) -> None:
        super().update(dt)
        # TODO: 检查前进方向是否有植物
        # TODO: 检查是否已经接触到植物
        # 获取动画状态
        controller = self.animation.get_current_controller()
        # 更新方向向量
        self.direction = self.path_finder.next_move_direction()
        # 处理僵尸冰冻
        if self.iced_remain_time > 0:
            self.freeze()
        # 处理僵尸死亡事件
        if self.get_state() == 'dying' and isinstance(controller, OncePlayController) and controller.over:
            # 渐隐消失
            self.fading(dt)
        if not self.is_alive() and self.get_state() != 'dying':
            self.dying()
        # 处理僵尸受击
        if self.hurt_state:
            self.hit_flash(dt)
        # 处理僵尸移动
        if self.get_state() == 'walk':
            self.move(dt)


class ConfigZombie(GenericZombie):
    """
    基于json文件的僵尸，从配置文件中读取僵尸数据
    """

    def __init__(self, config: ZombieConfig, state_machine: AbstractZombieStateMachine,
                 group: Union[pygame.sprite.Group, list]):
        GenericZombie.__init__(
            self,
            group, random.randint(int(config.min_health), int(config.max_health)),
            StatefulAnimation(config.animation.get_random_animation_group(), config.animation.init_state),
            state_machine,
            config.speed,
            zombie_offset=config.zombie_offset
        )

    @classmethod
    def from_id(cls, group: pygame.sprite.Group, config_id: str) -> ConfigZombie:
        """
        从配置文件创建对象
        :param group: 精灵组
        :param config_id: 配置文件id
        :return:
        """
        config = CharacterConfigManager().get_config(config_id)
        if isinstance(config, ZombieConfig): raise Exception("The specified config is not a zombie")
        return cls(cast(config, ZombieConfig), group)


@ZombieCreator.register_zombie('normal_zombie')
class NormalZombie(ConfigZombie):
    """
    最普通的僵尸
    """
    def __init__(self, group: Union[pygame.sprite.Group, list]):
        super().__init__(CharacterConfigManager().get_zombie_config('normal_zombie'), ZombieStateMachine(), group)


@ZombieCreator.register_zombie('buckethead_zombie')
class BucketheadZombie(ConfigZombie):
    """
    铁桶僵尸
    """
    def __init__(self, group: Union[pygame.sprite.Group, list]):
        super().__init__(CharacterConfigManager().get_zombie_config('buckethead_zombie'),
                         BucketheadZombieStateMachine(), group)

    def update(self, dt: float):
        super().update(dt)
        if self.health <= 270 and self.get_state() == 'walk_with_bucket':
            self.walk()
        # walk状态在父类中已处理，无需重复处理
        if self.get_state() in ['walk_with_bucket', 'walk_with_broken_bucket']:
            self.move(dt)


class ZombiePathFinder:
    """
    僵尸寻路器
    """

    def __init__(self, zombie: AbstractZombie):
        self.zombie = zombie
        if self.zombie.direction.x == 0:
            raise Exception("Zombie's direction.x cannot be 0")
        self.grid = self.zombie.level.grid
        self.change_row_offset_angle = 10

    def is_at_cell_vertical(self, cell: AbstractPlantCell) -> bool:
        """
        僵尸的横坐标是否到达指定单元格的横坐标
        """
        delta_x = abs(cell.get_center_pos().x - self.zombie.get_center_pos().x)
        if delta_x < 10:
            # 小于10像素视为到达
            return True
        return False

    def is_at_cell_horizontal(self, cell: AbstractPlantCell) -> bool:
        """
        僵尸的纵坐标是否到达指定单元格的纵坐标
        """
        delta_y = abs(cell.get_center_pos().y - self.zombie.get_offset_center_position().y)
        if delta_y < 10:
            # 小于10像素视为到达
            return True
        return False

    def find_cell_range_with_direction(self, cells: list[AbstractPlantCell]) -> tuple[int, int]:
        """
        在严格递增的单元格中二分查找僵尸处在哪两个格子之间，考虑僵尸行走方向
        :param cells: 单元格列表（x 坐标严格递增）
        :return: (i, j)，僵尸处于 cells[i] 和 cells[j] 之间
        """
        left, right = 0, len(cells) - 1
        target_x = self.zombie.get_offset_center_position().x

        if target_x < cells[0].get_center_pos().x:
            return -1, 0
        if target_x > cells[-1].get_center_pos().x:
            return len(cells) - 1, -1

        while left <= right:
            mid = (left + right) // 2
            mid_x = cells[mid].get_center_pos().x

            if target_x < mid_x:
                right = mid - 1
            elif target_x > mid_x:
                left = mid + 1
            else:  # target_x == mid_x
                if self.zombie.direction.x > 0:  # 向右
                    # 向右应该返回 (mid, mid + 1)，但确保 mid > 0
                    return mid, mid + 1 if mid + 1 < len(cells) else -1
                else:  # 向左
                    # 向左应该返回 (mid - 1, mid)，但确保 mid + 1 < len
                    return mid - 1 if mid > 0 else -1, mid

        # 此时 left > right，说明在某两个单元格之间
        # 确保 left 在合法范围
        if 0 < left < len(cells):
            return left - 1, left

        raise Exception(
            'Cannot locate the position of zombie: ({}, {}), row: {}'.format(self.zombie.get_offset_center_position().x,
                                                                             self.zombie.get_offset_center_position().y,
                                                                             self.zombie.row))

    def next_move_direction(self) -> pygame.Vector2:
        """
        僵尸的下一帧方向向量
        """
        cells = self.grid.get_row_of(self.zombie.row)
        left, right = self.find_cell_range_with_direction(cells)
        result: Union[pygame.Vector2, None] = None
        target_index = None

        if left == -1 and self.zombie.direction.x == -1:
            result = pygame.Vector2(-1, 0)
            target_index = -1

        if right == -1 and self.zombie.direction.x == 1:
            result = pygame.Vector2(1, 0)
            target_index = -1

        if target_index == -1: return result
        if self.zombie.direction.x < 0:
            if self.is_at_cell_vertical(cells[left]):
                if left - 1 < 0:
                    result = pygame.Vector2(-1, 0)
                    target_index = -1
                else:
                    result = (cells[left - 1].get_center_pos() - self.zombie.get_offset_center_position()).normalize()
                    target_index = left - 1
            else:
                result = (cells[left].get_center_pos() - self.zombie.get_offset_center_position()).normalize()
                target_index = left
        if self.zombie.direction.x > 0:
            if self.is_at_cell_vertical(cells[right]):
                if right + 1 > len(cells) - 1:
                    result = pygame.Vector2(1, 0)
                    target_index = -1
                else:
                    result = (cells[right + 1].get_center_pos() - self.zombie.get_offset_center_position()).normalize()
                    target_index = right + 1
            else:
                result = (cells[right].get_center_pos() - self.zombie.get_offset_center_position()).normalize()
                target_index = right

        if result is None or target_index is None: raise Exception('Cannot find a valid direction for the zombie!')

        if target_index == -1 or self.is_at_cell_horizontal(cells[target_index]):
            return result

        result.x *= 0.1
        result = result.normalize()
        return result
