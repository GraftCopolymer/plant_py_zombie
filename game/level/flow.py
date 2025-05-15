from typing import TYPE_CHECKING, Callable, Generator

if TYPE_CHECKING:
    from game.level.level_scene import LevelScene

def part_wait(duration: float):
    timer = 0
    while timer < duration:
        timer += yield

class FlowPart:
    """
    关卡执行流结点
    """
    def __init__(self, func: Callable[..., Generator]):
        self.func: Callable[..., Generator] = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class FlowController:
    """
    关卡执行流控制器
    传入一个FlowPart列表并以此执行，期间需调用update来更新
    执行期间可动态新增FlowPart
    """
    def __init__(self, level: 'LevelScene'):
        self.level = level
        self.steps = self._build_steps()
        self.current_step = None
        self.is_running = False
        self.is_pause = True
        self.parts: list[FlowPart] = []

    def _build_steps(self):
        """
        将每一步构建成生成器（协程）
        """
        index = 0
        while index < len(self.parts):
            yield self.parts[index]()
            index += 1
        yield

    def start(self):
        """
        开始流执行，开始后调用update方法才会起作用
        若当前没有flow parts，则会启动失败
        :return:
        """
        self.steps = self._build_steps()  # 重置生成器
        self.current_step = next(self.steps)
        if self.current_step:
            self.current_step.send(None)
            self.is_running = True
            self.is_pause = False
        else:
            self.reset_flow()

    def reset_flow(self) -> None:
        """
        重置流至初始状态（保留已经添加的part）
        """
        self.steps = self._build_steps()
        self.current_step = None
        self.is_running = False

    def reset_and_clear(self):
        self.reset_flow()
        self.clear_flow()

    def clear_flow(self):
        """
        清除所有part
        """
        self.parts.clear()

    def pause(self):
        """
        暂停流执行
        """
        if not self.is_running: return
        self.is_pause = True

    def resume(self):
        """
        恢复流执行
        """
        if not self.is_running: return
        self.is_pause = False

    def is_paused(self):
        """
        当前是否已暂停
        """
        return self.is_running and self.is_pause

    def update(self, dt: float):
        """
        由外界调用，dt值可在FlowPart的函数中通过yield获取
        :param dt: 自上次更新以来经过的毫秒数
        """
        if not self.is_running or not self.current_step or self.is_pause:
            return
        try:
            self.current_step.send(dt)
        except StopIteration:
            # 当前步骤完成，进入下一步
            self.current_step = next(self.steps, None)
            if self.current_step:
                self.current_step.send(None)
            if self.current_step is None:
                self.is_running = False  # 所有步骤执行完毕

    def add_part(self, part: FlowPart):
        """
        将指定FlowPart添加到当前流中，可在流执行时动态新增
        :param part: 需要添加的part
        """
        self.parts.append(part)
