from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from game.character.zombie import AbstractZombie


class ZombieCreator:
    # 禁止直接修改该字段
    zombie_registries = {}

    @staticmethod
    def register_zombie(name: str):
        def wrapper(zombie_cls: Type['AbstractZombie']):
            ZombieCreator.zombie_registries[name] = zombie_cls
            return zombie_cls
        return wrapper

    @staticmethod
    def create_zombie(name: str) -> 'AbstractZombie':
        if name not in ZombieCreator.zombie_registries:
            raise Exception('No such Zombie!')
        return ZombieCreator.zombie_registries[name]([])