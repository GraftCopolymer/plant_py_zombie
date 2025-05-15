import abc
from abc import abstractmethod
from typing import Union, Optional

import pygame.sprite
from pygame import Surface, Vector2

from game.character import Position
from base.config import LAYERS

class GameSprite(pygame.sprite.Sprite, abc.ABC):
    """
    游戏精灵
    """
    def __init__(self, group: Union[pygame.sprite.Group, list], image: Union[Surface, None], position: Position = pygame.math.Vector2((0,0)), speed: int = 0, z: int = LAYERS['main']):
        pygame.sprite.Sprite.__init__(self, group)
        self.group = group
        self.world_pos = position
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = speed
        self.rect: Union[pygame.Rect, None] = None
        self.image = image
        self.z = z
        # 图片偏移（由于有些gif图有大量透明像素，图片矩形并不适合用来做碰撞检测，所以图片需要和矩形框分开计算，该变量是为了将图片与矩形框对齐的偏移量）
        self.image_offset: pygame.Vector2 = pygame.Vector2(0, 0)
        self.rect_offset: pygame.Vector2 = pygame.Vector2(0,0)
        self._old_rect_offset: Vector2 = self.rect_offset
        # 是否显示
        self.display = True

    @abstractmethod
    def update(self, dt: float) -> None:
        if self.rect is None: return
        self.rect.topleft = self.world_pos
        # if self.rect_offset.x != self._old_rect_offset.x or self.rect_offset.y != self._old_rect_offset.y:
        #     self.rect.move_ip(self._old_rect_offset)
        #     self.world_pos += self._old_rect_offset
        #     self.rect.move_ip(-self.rect_offset)
        #     self.world_pos -= self.rect_offset
        #     self._old_rect_offset = self.rect_offset

    @abstractmethod
    def setup_sprite(self, *args, **kwargs) -> None:
        """
        该方法由子类重写，用于延迟挂载对象, 在GameSprite声明周期中仅会调用一次
        """
        self.mount(*args, **kwargs)

    def debug_draw(self, surface: Surface, camera_pos: Vector2) -> None:
        """
        用于绘制debug图形
        :param surface: 绘制表面，由相机传入
        :param camera_pos: 相机位置
        """
        pass

    def get_z(self):
        return self.z

    def set_position(self, position: Position):
        pos = position.copy()
        self.world_pos = pos
        if self.rect is None: return
        self.move_rect_to(pos)

    def set_center_pos(self, pos: pygame.Vector2) -> None:
        if self.rect is None: raise Exception("the sprite don't have a rect")
        self.rect.center = tuple(pos)
        self.world_pos = pygame.Vector2(self.rect.topleft)

    def get_center_pos(self) -> pygame.Vector2:
        if self.rect is None:
            raise Exception("the sprite don't have a rect")
        return pygame.Vector2(self.rect.center)

    def move_rect_to(self, topleft: pygame.Vector2):
        if self.rect is not None:
            self.rect.topleft = topleft.copy()

    def is_visible(self, override_rect: Optional[pygame.Rect]=None) -> bool:
        """
        该精灵是否可见
        :param override_rect: 重载矩形，若提供了该参数，则会使用该参数进行检测，而非对象自带的矩形
        :return: 若该精灵可被用户看见，则返回True，否则返回False
        """
        from base.cameragroup import CameraGroup
        from game.game import Game
        target_rect = override_rect or self.rect
        if isinstance(self.group, CameraGroup): # 若当前group是摄像机，则检测是否在摄像机范围内
            # 检测是否在摄像机范围内
            camera_world_rect = pygame.Rect(self.group.world_pos, Game.screen_size)
            if not target_rect: # 当前对象没有rect对象, 则检查其坐标是否在摄像机范围内
                return camera_world_rect.collidepoint(self.world_pos)
            else:
                return camera_world_rect.colliderect(target_rect)
        elif isinstance(self.group, pygame.sprite.Group):
            screen_world_rect = pygame.Rect((0,0), Game.screen_size)
            if not target_rect: # 当前对象没有rect对象, 则检查其坐标是否在摄像机范围内
                return screen_world_rect.collidepoint(self.world_pos)
            else:
                return screen_world_rect.colliderect(target_rect)
        else:
            return False

    def destroy(self):
        """
        在此处进行资源释放操作
        """
        self.unmount()

    def unmount(self):
        """
        对象取消挂载, 在此处取消事件订阅
        """
        pass

    def mount(self, *args, **kwargs):
        """
        对象挂载
        """
        pass


    def __copy__(self):
        cls = self.__class__
        res = cls.__new__(cls)

        # 基础字段复制
        res.group = self.group  # 引用共享，不能直接 copy() 否则破坏精灵关系
        # 初始化 Sprite 状态（需要重新注册到 group）
        pygame.sprite.Sprite.__init__(res, res.group)

        res.world_pos = self.world_pos.copy()
        res.direction = self.direction.copy()
        res.speed = self.speed
        res.z = self.z

        # 图像和矩形
        res.image = self.image.copy()  # Surface 通常共享即可
        res.rect = self.rect.copy() if self.rect else None

        # 偏移量
        res.image_offset = self.image_offset.copy()
        res.rect_offset = self.rect_offset.copy()
        res._old_rect_offset = self._old_rect_offset.copy()

        # 显示状态
        res.display = self.display

        return res