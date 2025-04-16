import abc
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.character.bullets import Bullet


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
    贴近时爆炸
    """
    @abstractmethod
    def boom(self) -> None: pass
    @abstractmethod
    def get_boom_damage(self) -> float: pass
    @abstractmethod
    def get_range(self) -> float: pass