import abc
from typing import Callable, TypeVar


class Listenable(abc.ABC):
    """
    可监听对象, 对象值变化时会通知监听者
    """
    def __init__(self):
        self.listeners: list[Callable[[],None]] = []

    def add_listener(self, callback: Callable[[], None]):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[], None]):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def notify_listener(self):
        """
        通知监听者
        """
        for listener in self.listeners:
            listener()

    def clear(self):
        """
        移除所有监听者
        """
        self.listeners.clear()


T = TypeVar('T')
class ListenableValue(Listenable):
    def __init__(self, init_value: T):
        super().__init__()
        self._value = init_value

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_val: T) -> None:
        self._value = new_val
        # 通知监听者
        self.notify_listener()