from __future__ import annotations
import abc
import enum
import random
from abc import abstractmethod
from ctypes import cast

import pygame

from base.animation import StatefulAnimation, OncePlayController
from base.sprite.game_sprite import GameSprite
from game.character import Position
from game.character.character_config import ZombieConfig, ConfigManager


class ZombieState(enum.Enum):
    IDLE = 'idle'
    WALK = 'walk'
    DYING = 'dying'
    ATTACK = 'attack'


class AbstractZombie(GameSprite, abc.ABC):
    def __init__(self, group: pygame.sprite.Group, health: float, animation: StatefulAnimation, init_state: ZombieState, position: Position = pygame.math.Vector2((0, 0))):
        GameSprite.__init__(self, group, animation.get_current_image(), position)
        self.animation = animation
        self.health = health
        assert init_state.value in animation.get_states()
        self.state = init_state

    def update(self, dt: float) -> None:
        GameSprite.update(self, dt)
        self.animation.update(dt)
        self.image = self.animation.get_current_image()
        self.rect.center = (int(self.position.x), int(self.position.y))

    def get_state(self) -> ZombieState:
        return self.state

    @abstractmethod
    def move(self, dt: float) -> None: pass


class GenericZombie(AbstractZombie):
    """
    通用僵尸类
    提供生命值，idle、walk、attack、dying行为
    如需更多行为，请继承该类进行扩展
    """
    def __init__(self, group: pygame.sprite.Group, health: float, animation: StatefulAnimation, speed: float):
        AbstractZombie.__init__(self, group, health, animation, ZombieState(animation.get_current_state()))
        self.speed = speed
        self.rect = animation.get_current_image().get_rect()
        self.rect.center = (int(self.position.x), int(self.position.y))
        self.direction = pygame.math.Vector2([-1,0])
        self.died_fading_time = 2000
        self.fading_timer = 0

    def move(self, dt: float) -> None:
        super().move(dt)
        horizontal_dis = dt / 1000 * self.speed * self.direction
        self.set_position(self.position + horizontal_dis)

    def set_position(self, position: Position):
        super().set_position(position)
        if self.rect is not None:
            if self.position.x < 0:
                self.position.x = 0
            self.rect.center = (int(self.position.x), int(self.position.y))

    def attack(self):
        # 播放攻击动画
        self.animation.change_state(ZombieState.ATTACK.value)
        self.state = ZombieState.ATTACK

    def walk(self):
        self.animation.change_state(ZombieState.WALK.value)
        self.state = ZombieState.WALK

    def idle(self):
        # 播放idle动画
        self.animation.change_state(ZombieState.IDLE.value)
        self.state = ZombieState.IDLE

    def dying(self):
        # 播放死亡动画
        self.animation.change_state(ZombieState.DYING.value)
        self.state = ZombieState.DYING

    def fading(self, dt: float):
        alpha = int(255 * max(1 - self.fading_timer / self.died_fading_time, 0))
        self.image.set_alpha(alpha)
        self.fading_timer += dt
        if self.fading_timer >= self.died_fading_time:
            self.group.remove(self)
            self.fading_timer = 0
            print("已清除僵尸")

    def update(self, dt: float) -> None:
        super().update(dt)
        # TODO: 检查前进方向是否有植物
        # TODO: 检查是否已经接触到植物
        # 获取动画状态
        controller = self.animation.get_current_controller()
        if self.state == ZombieState.DYING and isinstance(controller, OncePlayController) and controller.over:
            # 渐隐消失
            self.fading(dt)
        if self.health <= 0:
            self.dying()
        if self.state == ZombieState.WALK:
            self.move(dt)


class ConfigZombie(GenericZombie):
    """
    基于json文件的僵尸，从配置文件中读取僵尸数据
    """
    def __init__(self, config: ZombieConfig, group: pygame.sprite.Group):
        GenericZombie.__init__(
            self,
            group,random.randint(int(config.min_health), int(config.max_health)),
            StatefulAnimation(config.get_random_animation_group(), config.init_state),
            config.speed
        )

    @classmethod
    def from_id(cls, group: pygame.sprite.Group, config_id: str) -> ConfigZombie:
        """
        从配置文件创建对象
        :param group: 精灵组
        :param config_id: 配置文件id
        :return:
        """
        config = ConfigManager().get_config(config_id)
        if isinstance(config, ZombieConfig): raise Exception("The specified config is not a zombie")
        return cls(cast(config, ZombieConfig), group)
