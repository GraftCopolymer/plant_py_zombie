import json
import random
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.character.zombie import AbstractZombie
from game.level.zombie_creator import ZombieCreator


class ZombieWaveScheduler:
    """
    僵尸波次调度器, 调度器中的时间单位均为ms
    """
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.waves = self.config["waves"]
        self.duration = self.config.get("duration", 180000)
        self.max_concurrent = self.config.get("max_concurrent_zombies", 10)
        self.default_interval = self.config.get("default_spawn_interval", 3000)

        self.timer = 0
        self.current_wave_index = 0
        self.last_spawn_time = 0

        self.spawned_zombie_count = 0  # 当前场上僵尸数
        self.get_alive_zombie_count: Callable[[], int] = lambda: 0

    def update_and_gen(self, dt: float) -> Optional['AbstractZombie']:
        """
        更新调度器并在合适的时候返回创建的僵尸
        :return: None 或 生成的僵尸
        """
        if self.get_progress() == 1: return None
        self.timer += dt

        # 选中当前波次
        while (self.current_wave_index + 1 < len(self.waves) and
               self.waves[self.current_wave_index + 1]["time"] <= self.timer):
            self.current_wave_index += 1

        current_wave = self.waves[self.current_wave_index]
        interval = current_wave.get("spawn_interval", self.default_interval)

        if self.timer - self.last_spawn_time >= interval:
            if self.get_alive_zombie_count() < self.max_concurrent:
                self.last_spawn_time = self.timer
                return self._generate_zombie(current_wave["zombies"])

        return None

    def _generate_zombie(self, zombie_def_list) -> Optional['AbstractZombie']:
        pool = []
        for z in zombie_def_list:
            pool.extend([z["type"]] * z["frequency"])
        if len(pool) == 0:
            return None
        zombie_name = random.choice(pool)
        return ZombieCreator.create_zombie(zombie_name)

    def is_finished(self):
        return self.timer >= self.duration

    def set_alive_zombie_count_getter(self, func: Callable[[], int]):
        self.get_alive_zombie_count = func

    def get_current_warning(self) -> str:
        wave = self.waves[self.current_wave_index]
        return wave.get("warning", "")

    def get_progress(self) -> float:
        """
        :return: 当前调度器进度，为一个0.0~1.0之间的float
        """
        return min(self.timer / self.duration, 1.0)