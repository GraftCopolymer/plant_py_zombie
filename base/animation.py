import abc
import enum
from abc import abstractmethod
from typing import Sequence, Optional, List, Union

from PIL import Image
import pygame
from pygame import SurfaceType


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


class Animation:
    """
    动画，内部实现了帧动画播放逻辑
    对应AnimationType的multi_image
    """
    def __init__(self,
                 images: Sequence[SurfaceType],
                 play_mode: PlayMode = PlayMode.LOOP,
                 interval: int = 150,
                 init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0):
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

    def get_image(self) -> SurfaceType:
        return self.images[self.current_frame]

    @classmethod
    def from_paths(cls, image_paths: List[str], play_mode: PlayMode, interval: int,
                   init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0):
        images = []
        for path in image_paths:
            images.append(pygame.image.load(path).convert())
        return cls(images, play_mode, interval, init_frame, play_speed_scale)


class GifAnimation(Animation):
    """
    使用gif作为帧动画的动画
    对应AnimationType的gif
    """

    def __init__(self, path: str, play_mode: PlayMode = PlayMode.LOOP, interval: int = 150,
                 init_frame: Optional[int] = 0, play_speed_scale: Optional[float] = 1.0, ):
        Animation.__init__(self, self._load_gif(path), play_mode, interval, init_frame, play_speed_scale)

    def _load_gif(self, gif_path: str) -> list[SurfaceType]:
        gif = Image.open(gif_path)
        images = []
        while True:
            frame = gif.convert("RGBA")
            pygame_frame = pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA").convert_alpha()
            images.append(pygame_frame)
            try:
                gif.seek(len(images))
            except EOFError:
                return images

class AnimationFactory:
    @staticmethod
    def create_animation(animation_type: AnimationType,
                         source: Union[List[str], str],
                         play_mode: str = PlayMode.LOOP.value,
                         interval: int = 150,
                         init_frame: Optional[int] = 0,
                         play_speed_scale: Optional[float] = 1.0,
                         **kwargs) -> Animation:
        """
        动画工厂方法：根据类型创建 Animation 或 GifAnimation 实例

        :param animation_type: 动画类型，'multi_image' 或 'gif'
        :param source: 如果是 multi_image，则是图片路径列表；如果是 gif，则是 gif 文件路径
        :param play_mode: 播放模式
        :param interval: 帧间隔时间
        :param init_frame: 初始帧
        :param play_speed_scale: 播放速度因子
        :return: 对应类型的 Animation 实例
        """

        play_mode = PlayMode(kwargs.get('play_mode', PlayMode(play_mode)))
        interval = kwargs.get('interval', interval)
        init_frame = kwargs.get('init_frame', init_frame)
        play_speed_scale = kwargs.get('play_speed_scale', play_speed_scale)

        if animation_type == AnimationType.MULTI_IMAGE:
            if not isinstance(source, list):
                raise TypeError("multi_image 类型的 source 应该是 List[str]")
            return Animation.from_paths(source, play_mode, interval, init_frame, play_speed_scale)

        elif animation_type == AnimationType.GIF:
            if not isinstance(source, str):
                raise TypeError("gif 类型的 source 应该是 str（gif 路径）")
            return GifAnimation(source, play_mode, interval, init_frame, play_speed_scale)

        else:
            raise ValueError(f"未知的动画类型: {animation_type}")


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

    def get_current_image(self) -> SurfaceType:
        return self.animations[self.state].get_image()

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

    def next_frame(self) -> int:
        frame = self.current_frame
        if not self.over:
            self.current_frame += 1
        if self.current_frame == self.frames - 1:
            self.over = True
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
