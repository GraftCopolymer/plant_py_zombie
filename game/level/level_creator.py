from typing import Type, Optional

from game.level.level_scene import LevelScene


class LevelCreator:
    """
    关卡创建器
    """
    # 禁止直接修改该字段
    level_registries = {}

    @staticmethod
    def register_level(name: str):
        def wrapper(level_cls: Type['LevelScene']):
            print(f'已加载关卡: {level_cls}')
            LevelCreator.level_registries[name] = level_cls
            return level_cls
        return wrapper

    @staticmethod
    def create_level(name: str) -> 'LevelScene':
        if name not in LevelCreator.level_registries:
            raise Exception(f'No such level: {name}')
        return LevelCreator.level_registries[name]()

    @staticmethod
    def get_level_cls(name: str) -> Optional[Type['LevelScene']]:
        if name in LevelCreator.level_registries:
            return LevelCreator.level_registries[name]
        return None