from typing import TYPE_CHECKING, Callable, Generator, Optional

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
        # self.steps = self._build_steps() # 不需要在这里初始化，也不再是生成器
        self.current_step_generator = None # 当前正在执行的 FlowPart 对应的生成器实例
        self.is_running = False
        self.is_pause = True
        self.parts: list[FlowPart] = []
        self._current_part_index = 0 # 记录当前执行到哪个 FlowPart

    def _get_next_part_generator(self) -> Optional[Generator]:
        """
        获取下一个 FlowPart 对应的生成器实例
        """
        if self._current_part_index < len(self.parts):
            # 获取下一个 FlowPart 并调用它以获得其内部的生成器
            next_part = self.parts[self._current_part_index]
            self._current_part_index += 1
            return next_part() # 调用 FlowPart 会返回其 func 的生成器
        return None

    def start(self):
        """
        开始流执行，开始后调用update方法才会起作用
        若当前没有flow parts，则会启动失败
        :return:
        """
        if not self.parts:
            print("FlowController: No parts to start, starting failed.")
            self.reset_flow() # 确保状态正确
            return

        self.reset_flow() # 确保从头开始
        self.current_step_generator = self._get_next_part_generator()

        if self.current_step_generator:
            try:
                # 启动第一个步骤的生成器
                self.current_step_generator.send(None)
                self.is_running = True
                self.is_pause = False
            except StopIteration:
                # 如果第一个步骤瞬间完成 (例如，一个空的生成器)
                print("FlowController: First part finished immediately.")
                self._advance_to_next_part() # 尝试进入下一个
        else:
            self.reset_flow() # 没有可用的步骤，重置

    def reset_flow(self) -> None:
        """
        重置流至初始状态（保留已经添加的part）
        """
        self.current_step_generator = None
        self.is_running = False
        self.is_pause = True # 重置后默认暂停，等待start
        self._current_part_index = 0

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

    def _advance_to_next_part(self):
        """
        内部方法：前进到下一个 FlowPart
        """
        # 如果已暂停，则不前进
        if self.is_pause: return
        self.current_step_generator = self._get_next_part_generator()
        if self.current_step_generator:
            try:
                # 启动下一个步骤的生成器
                self.current_step_generator.send(None)
            except StopIteration:
                # 如果下一个步骤也瞬间完成
                print("FlowController: Subsequent part finished immediately.")
                self._advance_to_next_part() # 递归尝试下一个
        else:
            # 没有更多步骤了
            self.is_running = False
            self.is_pause = True # 所有步骤执行完毕，停止并暂停

    def update(self, dt: float):
        """
        由外界调用，dt值可在FlowPart的函数中通过yield获取
        :param dt: 自上次更新以来经过的毫秒数
        """
        if not self.is_running or not self.current_step_generator or self.is_pause:
            return

        try:
            self.current_step_generator.send(dt)
        except StopIteration:
            # 当前步骤完成，进入下一步
            self._advance_to_next_part()

    def add_part(self, part: FlowPart):
        """
        将指定FlowPart添加到当前流中，可在流执行时动态新增
        :param part: 需要添加的part
        """
        self.parts.append(part)
        print(f"FlowController: Added new part. Total parts: {len(self.parts)}")
