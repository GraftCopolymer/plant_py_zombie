import abc
from abc import abstractmethod
from typing import TYPE_CHECKING

from game.character.plant_state_machine import AbstractPlantStateMachine

if TYPE_CHECKING:
    from game.character.bullets import Bullet

"""
本文件的所有class视为接口使用
"""


class Shooter(abc.ABC):
    """
    发射某种子弹
    """
    @abstractmethod
    def shoot(self) -> None: pass
    @abstractmethod
    def get_bullet(self) -> 'Bullet': pass
    @abstractmethod
    def get_range(self) -> float: pass
    @abstractmethod
    def should_shoot(self) -> bool: pass

class Boomer(abc.ABC):
    """
    定时爆炸
    """
    @abstractmethod
    def boom(self) -> None: pass
    @abstractmethod
    def get_boom_damage(self) -> float: pass
    @abstractmethod
    def get_range(self) -> float: pass

class TimingAction(abc.ABC):
    """
    每隔一段时间做出一定操作的植物
    """
    @abstractmethod
    def getNextActionInterval(self) -> int:
        """
        下一次操作的时间间隔, 单位ms
        """
        pass

    @abstractmethod
    def doAction(self) -> None:
        """
        执行操作
        """
        pass

class StatefulPlant(abc.ABC):
    """
    有状态机的植物
    """
    @abstractmethod
    def get_state_machine(self) -> AbstractPlantStateMachine:
        """
        返回当前植物的状态机
        """
        pass

    @abstractmethod
    def handle_state(self, *args, **kwargs) -> None:
        """
        处理当前植物的状态
        """
        pass