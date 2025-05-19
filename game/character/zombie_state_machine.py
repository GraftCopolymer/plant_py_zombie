"""
僵尸状态机
"""

from __future__ import annotations

import abc

from game.level.state_machine import StateMachine, State


class AbstractZombieStateMachine(StateMachine, abc.ABC):
    def __init__(self):
        super().__init__()


class ZombieStateMachine(AbstractZombieStateMachine):
    def __init__(self):
        super().__init__()
        self.walk = State('walk')
        self.idle = State('idle')
        self.dying = State('dying')
        self.attack = State('attack')
        self.add_state(self.idle, {'walk'})
        self.add_state(self.walk, {'attack', 'dying'})
        self.add_state(self.dying, set())
        self.add_state(self.attack, {'dying', 'walk'})
        self.set_initial_state('walk')


class BucketheadZombieStateMachine(ZombieStateMachine):
    def __init__(self):
        super().__init__()
        # 顶着完整头盔走
        self.walk_with_bucket = State('walk_with_bucket')
        # 顶着破头盔走
        self.walk_with_broken_bucket = State('walk_with_broken_bucket')
        # 顶着头盔攻击
        self.attack_with_bucket = State('attack_with_bucket')
        # 注意，无头盔行走使用状态walk(父类中定义)
        self.add_state(self.walk_with_bucket, {'walk', 'walk_with_broken_bucket', 'attack', 'attack_with_bucket', 'dying'})
        self.add_state(self.walk_with_broken_bucket, {'walk', 'attack', 'dying'})
        self.add_state(self.attack_with_bucket, {'attack', 'dying', 'walk', 'walk_with_bucket'})
        self.add_transition_of(self.attack, {'walk_with_bucket', 'walk_with_broken_bucket', 'attack_with_bucket'})
        self.set_initial_state('walk_with_bucket')
