import pygame
from typing import List, Dict, Callable, Any, Union, Optional

from pygame import Vector2, Surface
from dataclasses import dataclass

from base.cameragroup import CameraGroup
from base.config import LAYERS
from base.sprite.game_sprite import GameSprite


@dataclass
class TextAnimation:
    """
    单个文本动画定义
    """
    duration: float  # 动画总时长（毫秒）
    start_value: Any  # 起始值（根据动画类型不同可以是不同数据结构）
    end_value: Any  # 结束值
    easing: Callable[[float], float] = lambda t: t  # 缓动函数


class AnimatedText(GameSprite):
    """
    单个动画文本实例
    """

    def __init__(
            self,
            group: Union[pygame.sprite.Group, list],
            text: str,
            position: Vector2, # 最终将变换到相机坐标系
            font: pygame.font.Font,
            color: pygame.Color,
            animations: Dict[str, TextAnimation],  # 支持的动画类型：'fade', 'move', 'scale'
            outline_width: int = 0,
            outline_color: Optional[pygame.Color] = None,
            duration: float = 3000,  # 默认显示时间
            world_mode: bool=False, # 是否使用世界坐标
            camera: Optional[CameraGroup]=None,# 相机
            once: bool= True # 显示完毕后立即从group中删除
    ):
        super().__init__(group, None, position=position)
        self.world_mode = world_mode
        self.camera = camera
        if not self.world_mode:
            if not self.camera: raise Exception('Please provide the camera, because the world_mode is True')
            self.camera.add_to_follow(self)
        self.border_width: int = outline_width
        self.border_color: Optional[pygame.Color] = outline_color
        self.z = LAYERS['text']
        self._original_pos = self.world_pos
        self.text = text
        self.font = font
        self.color = color
        self.duration = duration
        self.time_elapsed = 0.0
        self.animations = animations
        self.image = self._render_text(self.text, self.font, self.color, self.border_width, self.border_color)
        self.active = True
        self.once = once

        # 初始化动画状态
        self.alpha = 255
        if 'fade' in animations:
            self.alpha = animations['fade'].start_value

    def update(self, dt: float):
        self.time_elapsed += dt
        progress = min(self.time_elapsed / self.duration, 1.0)

        # 更新所有动画
        for anim_type, anim in self.animations.items():
            anim_progress = min(self.time_elapsed / anim.duration, 1.0) if anim.duration > 0 else 1.0
            eased_progress = anim.easing(anim_progress)

            if anim_type == 'fade':
                self.alpha = int(anim.start_value + (anim.end_value - anim.start_value) * eased_progress)
                self.image.set_alpha(self.alpha)
            elif anim_type == 'move':
                self.world_pos.x = self._original_pos.x + (anim.end_value.x - anim.start_value.x) * eased_progress
                self.world_pos.y = self._original_pos.y + (anim.end_value.y - anim.start_value.y) * eased_progress

            elif anim_type == 'scale':
                # 缩放需要重新渲染文本表面
                pass

        if progress >= 1.0:
            self.active = False

    def _render_text(self, text: str, font: pygame.font.Font, text_color: pygame.Color, outline_width: int,
                     outline_color: Optional[pygame.Color] = None) -> Surface:
        # 先渲染文字轮廓
        outline_color = outline_color or pygame.Color(0, 0, 0)
        base = font.render(text, True, outline_color)
        size = base.get_width() + 2 * outline_width, base.get_height() + 2 * outline_width
        outline_image = pygame.Surface(size, pygame.SRCALPHA)

        # 绘制轮廓（在不同偏移处绘制轮廓颜色的文字）
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    pos = (outline_width + dx, outline_width + dy)
                    outline_image.blit(font.render(text, True, outline_color), pos)

        # 绘制主文字
        outline_image.blit(font.render(text, True, text_color), (outline_width, outline_width))
        return outline_image

    def setup_sprite(self, *args, **kwargs) -> None:
        super().setup_sprite()
        pass


class TextAnimator:
    """
    文本动画管理器
    """

    def __init__(self, group: Union[pygame.sprite.Group, list]):
        self.group: Union[pygame.sprite.Group, list] = group
        self.texts: List[AnimatedText] = []

    def add_text_and_show(
            self,
            text: str,
            position: Union[Vector2, tuple],
            color: pygame.Color,
            animations: Dict[str, TextAnimation],
            world_mode: bool = False,  # 是否使用世界坐标
            camera: Optional[CameraGroup] = None,  # 相机
            once: bool=True, # 显示完毕后立即删除
            outline_width: int = 0,
            outline_color: Optional[pygame.Color] = None,
            duration: float = 3000,
            font_size: int = 16,
            font_path: str = 'resources/ui/STHeiti Light.ttc'
    ):
        if isinstance(position, tuple):
            position = Vector2(position)
        font = pygame.font.Font(font_path, font_size)
        text_obj = AnimatedText(self.group, text, position, font, color, animations, outline_width, outline_color,
                                duration, world_mode, camera, once)
        self.texts.append(text_obj)
        self.group.add(text_obj)

    def fade_in_text(self,
                     text: str,
                     position: Union[Vector2, tuple],
                     color: pygame.Color,
                     animation_duration: float = 300,
                     world_mode: bool = False,  # 是否使用世界坐标
                     camera: Optional[CameraGroup] = None,  # 相机
                     once: bool=True, # 显示完毕后立即删除
                     outline_width: int = 0,
                     outline_color: Optional[pygame.Color] = None,
                     duration: float = 3000,
                     font_size: int = 16,
                     font_path='resources/ui/STHeiti Light.ttc'
                     ):
        self.add_text_and_show(text, position, color, {'fade': TextAnimation(animation_duration, 0, 255)}, world_mode, camera, once, outline_width,
                               outline_color, duration,
                               font_size, font_path)

    def update(self, dt: float):
        for text in self.texts[:]:  # 遍历副本以便安全删除
            text.update(dt)
            if not text.active and text.once:
                self.texts.remove(text)
                if text in self.group:
                    self.group.remove(text)

    # 在 base/config.py 中添加常用缓动函数
    class Easing:
        @staticmethod
        def linear(t: float) -> float:
            return t

        @staticmethod
        def ease_in_quad(t: float) -> float:
            return t * t

        @staticmethod
        def ease_out_quad(t: float) -> float:
            return 1 - (1 - t) * (1 - t)
