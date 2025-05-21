from __future__ import annotations

from traceback import print_tb
from typing import Optional, Callable, Dict, Union

class State:
    """
    状态机状态
    """
    def __init__(self, name: str,
                 on_enter: Optional[Callable[[State], None]] = None,
                 on_exit: Optional[Callable[[State], None]] = None):
        self.name = name
        self.on_enter = on_enter
        self.on_exit = on_exit

class StateMachine:
    def __init__(self):
        self.states: Dict[str, State] = {}
        self.transitions: Dict[str, set[str]] = {}  # from: [to, to, ...]
        self.current_state: Optional[State] = None

    def add_state(self, state: State, allowed_transitions: Optional[set[str]]=None):
        self.states[state.name] = state
        self.transitions[state.name] = allowed_transitions if allowed_transitions is not None else set()

    def set_initial_state(self, state_name: str):
        if state_name not in self.states:
            raise ValueError(f"State '{state_name}' not defined.")
        self.current_state = self.states[state_name]
        if self.current_state.on_enter:
            self.current_state.on_enter(self.current_state)

    def can_transition_to(self, target_state_name: str) -> bool:
        if not self.current_state:
            return False
        return target_state_name in self.transitions.get(self.current_state.name, set())

    def set_transition_of(self, state: Union[str, State], allowed_transitions: set[str]):
        if isinstance(state, str):
            self.transitions[state] = allowed_transitions
        elif isinstance(state, State):
            self.transitions[state.name] = allowed_transitions
        else:
            raise Exception('Invalid type of state')

    def add_transition_of(self, state: Union[str, State], allowed_transitions: set[str]):
        if isinstance(state, str):
            self.transitions[state].union(allowed_transitions)
        elif isinstance(state, State):
            self.transitions[state.name].union(allowed_transitions)
        else:
            raise Exception('Invalid type of state')

    def transition_to(self, target_state_name: str) -> bool:
        if not self.can_transition_to(target_state_name):
            print(f"❌ Invalid transition: {self.current_state.name if self.current_state else None} → {target_state_name}")
            return False

        old_state = self.current_state
        new_state = self.states[target_state_name]

        if old_state.on_exit:
            old_state.on_exit(old_state)
        self.current_state = new_state
        if new_state.on_enter:
            new_state.on_enter(new_state)

        print(f"✅ Transitioned: {old_state.name} → {new_state.name}")
        return True

    def get_state(self) -> Optional[str]:
        """
        :return: 状态机当前状态
        """
        return self.current_state.name if self.current_state else None
