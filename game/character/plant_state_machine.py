"""
植物状态机
"""
import abc

from game.level.state_machine import StateMachine, State


class AbstractPlantStateMachine(StateMachine, abc.ABC):
    def __init__(self):
        super().__init__()

class WallnutStateMachine(AbstractPlantStateMachine):
    """
    坚果墙状态机
    """
    def __init__(self):
        super().__init__()
        # 健康状态
        self.healthy = State('healthy')
        # 一级破损状态
        self.cracked1 = State('cracked1')
        # 二级破损状态
        self.cracked2 = State('cracked2')
        self.add_state(self.healthy, {'cracked1', 'cracked2'})
        self.add_state(self.cracked1, {'cracked2'})
        self.add_state(self.cracked2, set()) # cracked2 状态无法再跳到其他状态
        self.set_initial_state('healthy')

class SunShroomStateMachine(AbstractPlantStateMachine):
    """
    阳光菇状态机
    """
    def __init__(self):
        super().__init__()
        self.small_idle = State('small_idle')
        self.big_idle = State('big_idle')
        self.sleep = State('sleep')
        self.add_state(self.small_idle, {'big_idle', 'sleep'})
        self.add_state(self.big_idle, {'sleep'})
        self.add_state(self.sleep)
        self.set_initial_state('small_idle')

class CherryBombStateMachine(AbstractPlantStateMachine):
    def __init__(self):
        super().__init__()
        self.ready_to_boom = State('ready_to_boom')
        self.boomed = State('boomed')
        self.add_state(self.ready_to_boom, {'boomed'})
        self.add_state(self.boomed)
        self.set_initial_state('ready_to_boom')