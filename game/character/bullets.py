import abc
import random
from abc import abstractmethod
from typing import Union, TYPE_CHECKING

import pygame
from pygame import Surface, Vector2

from base.animation import StatefulAnimation, OncePlayController
from base.resource_loader import ResourceLoader
from base.sprite.game_sprite import GameSprite
from game.character.zombie import AbstractZombie
from utils.utils import collide

if TYPE_CHECKING:
    from game.level.level_scene import LevelScene
    from game.character.plant import AbstractPlant


class Bullet(GameSprite, abc.ABC):
    """
    植物弹幕
    """
    def __init__(self, image: pygame.Surface):
        super().__init__([], image)
        self.owner: Union['AbstractPlant', None] = None
        # 是否仅攻击与其所有者在同一行的僵尸
        self.only_same_row = True
        # 子弹运行方向
        self.direction: pygame.Vector2 = pygame.Vector2(1, 0)
        # 子弹伤害
        self.damage = 0
        self.level: Union['LevelScene', None] = None
        # 边界矩形，超出该区域子弹视为不可见状态（需子类处理）
        from game.game import Game
        self.bound_rect = Game.screen.get_rect()

    def setup_sprite(self, group: pygame.sprite.Group, owner, level: 'LevelScene'):
        super().setup_sprite()
        self.owner = owner
        self.level = level
        # 将自己添加到场景中
        self.level.add_bullet(self)
        self.group = group

    def debug_draw(self, surface: Surface, camera_pos: Vector2) -> None:
        rect = self.rect.copy()
        rect.topleft -= camera_pos
        pygame.draw.rect(surface, 'red', rect, 2)

    @abstractmethod
    def update(self, dt: float) -> None:
        super().update(dt)

    def change_direction(self, new_direct: pygame.Vector2):
        self.direction = new_direct.normalize()

    @abstractmethod
    def hit_zombie(self, zombie: AbstractZombie) -> None: pass

class AnimatedBullet(Bullet, abc.ABC):
    def __init__(self):
        self.animation = self.load_animation()
        super().__init__(self.animation.get_current_image())

    @abstractmethod
    def load_animation(self) -> StatefulAnimation:
        """
        加载弹幕动画
        """
        pass

    def update(self, dt: float) -> None:
        super().update(dt)
        # 更新动画
        self.animation.update(dt)
        self.image = self.animation.get_current_image()

class StraightForwardBullet(Bullet, abc.ABC):
    """
    直来直去的子弹
    """

    def __init__(self, speed: float, damage: float, image: Surface, image_offset: Vector2 = Vector2(0, 0)):
        super().__init__(image)
        # 子弹速度
        self.speed = speed
        # 子弹伤害
        self.damage = damage
        self.rect = image
        self.image_offset = image_offset

    def random_bullet_offset(self) -> pygame.Vector2:
        """
        为了增添视觉效果和引入的获取在发射处纵向的随机小范围偏移
        :return:
        """
        offset = pygame.Vector2(20, 0)
        offset.y = random.randint(-18, -12)
        return offset

    def setup_sprite(self, group: pygame.sprite.Group, owner, level: 'LevelScene'):
        super().setup_sprite(group, owner, level)
        self.rect = self.image.get_rect()
        self.rect.center = tuple(
            pygame.Vector2(self.owner.rect.center) - self.rect_offset + self.random_bullet_offset())
        self.world_pos = self.rect.topleft

    def hit_zombie(self, zombie: AbstractZombie) -> None:
        # 调用僵尸受击方法
        zombie.hurt(self, self.damage)
        # 删除自己
        self.level.remove_bullet(self)

    def update(self, dt: float) -> None:
        super().update(dt)
        # 碰撞检测
        self.rect = self.image.get_bounding_rect().move(self.world_pos)

        collide_sprites = pygame.sprite.spritecollide(self, self.owner.group, False, collided=collide)
        zombies: list[AbstractZombie] = []
        for sprite in collide_sprites:
            if isinstance(sprite, AbstractZombie) and sprite.row == self.owner.cell.row:
                zombies.append(sprite)
        # 筛选出活着的僵尸
        alive_zombies = []
        for z in zombies:
            if z.is_alive(): alive_zombies.append(z)
        if len(alive_zombies) > 0:
            self.hit_zombie(random.choice(alive_zombies))

        from game.game import Game
        if not Game.bullet_in_screen(self):
            print('删除子弹')
            self.level.remove_bullet(self)
            return

        self.set_position(self.world_pos + self.speed * dt / 1000 * self.direction)


class PeaBullet(StraightForwardBullet):
    def __init__(self):
        super().__init__(300, 20, ResourceLoader().get_bullet_image('pea_bullet'), pygame.Vector2(5, 5))
        # 豌豆生成时离豌豆射手中心的偏移
        self.rect = self.image.get_bounding_rect()


class IcedPeaBullet(StraightForwardBullet):
    def __init__(self):
        super().__init__(300, 20, ResourceLoader().get_bullet_image('iced_pea_bullet'), Vector2(5, 5))
        self.iced_time = 5000

    def hit_zombie(self, zombie: AbstractZombie) -> None:
        super().hit_zombie(zombie)
        zombie.set_iced_remain_time(self.iced_time)
        zombie.set_speed_factor(0.6)


class JalapenoFire(AnimatedBullet):
    """
    火爆辣椒的火焰
    """
    fire_offset = Vector2(0, -35)
    def __init__(self):
        super().__init__()
        # 是否已经烫了一次僵尸
        self.fired = False

    def load_animation(self) -> StatefulAnimation:
        config = ResourceLoader().get_bullet_animation('jalapeno_fire_animation')
        return StatefulAnimation(config.get_random_animation_group(), config.init_state)

    def update(self, dt: float) -> None:
        super().update(dt)
        controller = self.animation.get_current_controller()
        if not self.fired:
            # 获取当前行的所有僵尸并烧死
            for z in self.level.zombies:
                if z.row == self.owner.cell.row:
                    self.hit_zombie(z)
            self.fired = True
        if isinstance(controller, OncePlayController) and controller.over:
            self.level.remove_bullet(self)

    def setup_sprite(self, group: pygame.sprite.Group, owner, level: 'LevelScene'):
        super().setup_sprite(group, owner, level)
        # 获取当前owner所在行的最左边的单元格的坐标
        row_num = self.owner.cell.row
        cells = self.level.grid.get_row_of(row_num)
        gen_pos = self.owner.world_pos
        if len(cells) > 0:
            first = cells[0]
            gen_pos = first.position + self.fire_offset
        self.set_position(gen_pos)


    def hit_zombie(self, zombie: AbstractZombie) -> None:
        """
        杀死僵尸
        """
        if hasattr(zombie, 'boom_dying') and callable(getattr(zombie, 'boom_dying')):
            zombie.boom_dying()
