from __future__ import annotations
import abc
import enum
import os
from abc import abstractmethod
from typing import Sequence, Optional, List, Union, Any

from PIL import Image
import pygame
from pygame import Surface


class PlayMode(enum.Enum):
    """
    播放模式
    """
    LOOP = 'loop'
    """
    循环播放，播放到末尾时再次回到开头
    """
    ONCE = 'once'
    """
    只播放一次
    """
    REVERSE_LOOP = 'reverse_loop'
    """
    循环播放，播放到末尾时从末尾帧开始播放到开头帧，循环往复
    """

class AnimationType(enum.Enum):
    MULTI_IMAGE = 'multi_image'
    GIF = "gif"
    SPRITE_SHEET = 'sprite_sheet'


class Animation:
    """
    动画，内部实现了帧动画播放逻辑
    对应AnimationType的multi_image
    """
    def __init__(self,
                 images: Sequence[Surface],
                 play_mode: PlayMode = PlayMode.LOOP,
                 interval: int = 150,
                 init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0, offset: pygame.Vector2=pygame.Vector2(0,0)):
        """
        :param images: 图片列表，将从该列表选取帧显示
        :param play_mode: 播放模式 PlayMode 类型
        :param interval: 每帧时间间隔
        :param init_frame: 初始帧
        :param play_speed_scale: 播放速度因子，越大播放速度越快
        """
        # 全部帧图像
        self.images = images
        # 全部帧数量
        self.frames = len(self.images)
        assert self.frames > 0
        assert 0 <= init_frame < self.frames
        # 当前帧索引
        self.current_frame = init_frame
        # 速度因子，越大则动画播放速度越快
        self.play_speed_scale = play_speed_scale
        # 动画是否暂停
        self.is_pause = False
        # 动画帧控制器
        self.controller = AnimatePlayController.of(play_mode, self.frames)
        # 每帧之间时间间隔(ms)
        self.interval = interval / play_speed_scale
        # 自上一次更新帧以来的累计时间(ms)
        self.time_accumulate = 0
        # 帧偏移，含义同GameSprite中的offset字段
        self.offset = offset

    def animate(self, dt: float):
        # 暂停时不执行动画逻辑
        if self.is_pause:
            return
        self.time_accumulate += dt
        if self.time_accumulate >= self.interval:
            self.current_frame = self.controller.next_frame()
            self.time_accumulate = 0

    def update(self, dt: float) -> None:
        self.animate(dt)

    def reset(self):
        """
        重置动画状态
        :return:
        """
        self.controller.reset()
        self.current_frame = 0
        self.is_pause = False
        self.time_accumulate = 0

    def play(self):
        self.is_pause = False

    def pause(self):
        self.is_pause = True

    def get_image(self) -> Surface:
        return self.images[self.current_frame]

    @classmethod
    def from_paths(cls, image_paths: List[str], play_mode: PlayMode, interval: int,
                   init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0, offset: pygame.Vector2 = pygame.Vector2(0,0)):
        images = []
        for path in image_paths:
            images.append(pygame.image.load(path).convert())
        return cls(images, play_mode, interval, init_frame, play_speed_scale, offset)


class GifAnimation(Animation):
    """
    使用gif作为帧动画的动画
    对应AnimationType的gif
    """

    def __init__(self, path: str, play_mode: PlayMode = PlayMode.LOOP, interval: int = 150,
                 init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0, offset: pygame.Vector2=pygame.Vector2(0,0)):
        Animation.__init__(self, self._load_gif(path), play_mode, interval, init_frame, play_speed_scale, offset)

    def _load_gif(self, gif_path: str) -> list[Surface]:
        gif = Image.open(gif_path)
        images = []
        while True:
            frame = gif.convert("RGBA")
            pygame_frame = pygame.image.frombytes(frame.tobytes(), frame.size, "RGBA").convert_alpha()
            images.append(pygame_frame)
            try:
                gif.seek(len(images))
            except EOFError:
                return images

class SpriteSheetAnimation(Animation):
    """
    精灵动画集动画
    对应AnimationType.SPRITE_SHEET
    """
    def __init__(self, path: str, frames_count: int, play_mode: PlayMode = PlayMode.LOOP, interval: int = 150,
                 init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0, offset: pygame.Vector2=pygame.Vector2(0,0)):
        Animation.__init__(self, self._load_sprite_sheet(path, frames_count),play_mode, interval, init_frame, play_speed_scale, offset)

    def _load_sprite_sheet(self, sheet_path: str, frames_count: int) -> list[Surface]:
        """
        加载精灵图集
        :param sheet_path: 精灵图集路径
        :return: 精灵图集对应的Surface列表
        """
        # 用 Pillow 加载图集
        image = Image.open(sheet_path).convert("RGBA")
        sheet_width, sheet_height = image.size

        frames = []
        frame_width = sheet_width // frames_count
        frame_height = sheet_height

        # 横向排列的帧
        for i in range(frames_count):
            # 裁剪出帧区域（左，上，右，下）
            box = (i * frame_width, 0, (i + 1) * frame_width, frame_height)
            frame = image.crop(box)

            # 转换为 pygame.Surface
            pygame_image = pygame.image.frombytes(frame.tobytes(), frame.size, "RGBA").convert_alpha()
            frames.append(pygame_image)

        return frames

class AnimationFactory:
    @staticmethod
    def create_animation(animation_type: AnimationType,
                         source: Union[List[str], str],
                         play_mode: str = PlayMode.LOOP.value,
                         interval: int = 150,
                         init_frame: Optional[int] = 0,
                         play_speed_scale: Optional[float] = 1.0,
                         offset: list[float, float] = (0,0),
                         **kwargs) -> Animation:
        """
        动画工厂方法：根据类型创建 Animation、GifAnimation、SpriteSheetAnimation 实例

        :param animation_type: 动画类型，'multi_image' 或 'gif'
        :param source: 如果是 multi_image，则是图片路径列表；如果是 gif，则是 gif 文件路径
        :param play_mode: 播放模式
        :param interval: 帧间隔时间
        :param init_frame: 初始帧
        :param play_speed_scale: 播放速度因子
        :param offset: 帧偏移
        :return: 对应类型的 Animation 实例
        """

        play_mode = PlayMode(kwargs.get('play_mode', PlayMode(play_mode)))
        interval = kwargs.get('interval', interval)
        init_frame = kwargs.get('init_frame', init_frame)
        play_speed_scale = kwargs.get('play_speed_scale', play_speed_scale)
        offset = pygame.Vector2(kwargs.get('offset', offset))

        if animation_type == AnimationType.MULTI_IMAGE:
            if not isinstance(source, list):
                raise TypeError("multi_image 类型的 source 应该是 List[str]")
            return Animation.from_paths(source, play_mode, interval, init_frame, play_speed_scale, offset)

        elif animation_type == AnimationType.GIF:
            if not isinstance(source, str):
                raise TypeError("gif 类型的 source 应该是 str（gif 路径）")
            return GifAnimation(source, play_mode, interval, init_frame, play_speed_scale, offset)

        elif animation_type == AnimationType.SPRITE_SHEET:
            frames_count: Union[int, None] = kwargs.get('frames_count', None)
            if frames_count is None: raise ValueError("请提供精灵图集的帧数量")
            return SpriteSheetAnimation(source, frames_count, play_mode, interval, init_frame, play_speed_scale, offset)

        else:
            raise ValueError(f"未知的动画类型: {animation_type}")

class AnimationLoader:
    @staticmethod
    def load(animation_data: dict[str, list[dict[str, Any]]], root_path: str) -> dict[str, list[Animation]]:
        """
        从字典数据加载动画
        :param animation_data: 动画的字典数据，需符合一定的格式，见README
        :param root_path: 动画数据中的资源的根路径
        :return: 有状态动画对象
        """
        animations: dict[str, list[Animation]] = {}
        state: str
        anims: list[dict[str, Any]]
        for state, anims in animation_data.items():
            # 解析动画
            if not isinstance(anims, list): raise Exception("Each value of state of animations must be list type")
            if len(anims) == 0: raise Exception("Each value of state of animations mustn't be empty")
            anim: dict[str, str]
            for anim in anims:
                animation_type: AnimationType = AnimationType(anim['type'])
                if state not in animations:
                    animations[state] = []
                source = None
                if isinstance(anim['frames'], str):
                    source = os.path.join(root_path, anim['frames'])
                elif isinstance(anim['frames'], list):
                    source = []
                    for p in anim['frames']:
                        source.append(os.path.join(root_path, p))
                animations[state].append(
                    AnimationFactory.create_animation(animation_type, source, **anim))
        return animations


class StatefulAnimation:
    """
    带状态的动画, 可在不同状态对应的动画中切换播放
    """
    def __init__(self, state_animations: dict[str, Animation], init_state: str):
        self.animations = state_animations
        assert init_state in state_animations
        self.state = init_state

    def change_state(self, new_state: str) -> None:
        if new_state not in self.animations:
            raise Exception("Invalid animation state")
        self.state = new_state
        # 重置动画状态
        self.reset()

    def play(self):
        self.animations[self.state].play()

    def pause(self):
        self.animations[self.state].pause()

    def reset(self):
        self.animations[self.state].reset()

    def get_states(self):
        """
        :return: 返回所有状态
        """
        return self.animations.keys()

    def get_current_state(self) -> str:
        return self.state

    def get_current_image(self) -> Surface:
        return self.animations[self.state].get_image().copy()

    def get_current_animation(self) -> Animation:
        return self.animations[self.state]

    def update(self, dt: float):
        self.animations[self.state].update(dt)

    def get_current_controller(self):
        return self.animations[self.state].controller

class AnimatePlayController(abc.ABC):
    def __init__(self, frames: int, init_frame: Optional[int] = 0):
        assert frames > 0
        assert 0 <= init_frame < frames
        self.current_frame = init_frame
        self.frames = frames

    @abstractmethod
    def next_frame(self) -> int:
        pass

    def reset(self) -> None:
        self.current_frame = 0

    @classmethod
    # 获取特定类型的播放控制器
    def of(cls, controller_type: PlayMode, frames: int):
        assert frames > 0;
        if controller_type == PlayMode.LOOP:
            return LoopPlayController(frames)
        elif controller_type == PlayMode.ONCE:
            return OncePlayController(frames)
        elif controller_type == PlayMode.REVERSE_LOOP:
            return ReverseLoopPlayController(frames)
        else:
            raise "Invalid Play Mode"


class LoopPlayController(AnimatePlayController):
    def __init__(self, frames: int, init_frame: Optional[int] = 0):
        AnimatePlayController.__init__(self, frames, init_frame)

    def next_frame(self) -> int:
        frame = self.current_frame
        self.current_frame = (self.current_frame + 1) % self.frames
        return frame


class OncePlayController(AnimatePlayController):
    def __init__(self, frames: int, init_frame: Optional[int] = 0):
        AnimatePlayController.__init__(self, frames, init_frame)
        # 是否已经播放完毕
        self.over = False
        print(f'总帧数: {self.frames}')

    def next_frame(self) -> int:
        frame = self.current_frame
        if self.current_frame == self.frames - 1:
            self.over = True
        if not self.over:
            self.current_frame += 1
        return frame

    def reset(self) -> None:
        super().reset()
        self.over = False


class ReverseLoopPlayController(AnimatePlayController):
    class Status(enum.Enum):
        FORWARD = 1
        REVERSE = 2

    def __init__(self, frames: int, init_frame: Optional[int] = 0):
        AnimatePlayController.__init__(self, frames, init_frame)
        self.status = ReverseLoopPlayController.Status.FORWARD

    def next_frame(self) -> int:
        frame = self.current_frame
        if self.status == ReverseLoopPlayController.Status.FORWARD:
            if self.current_frame == self.frames - 1:
                self.status = ReverseLoopPlayController.Status.REVERSE
                self.current_frame = self.frames - 2
            else:
                self.current_frame += 1

        if self.status == ReverseLoopPlayController.Status.REVERSE:
            if self.current_frame == 0:
                self.status = ReverseLoopPlayController.Status.FORWARD
                self.current_frame = min(self.frames - 1, 1)  # 确保不会超出索引范围
            else:
                self.current_frame -= 1
        return frame

    def reset(self) -> None:
        super().reset()
        self.status = ReverseLoopPlayController.Status.FORWARD
