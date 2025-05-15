from typing import Type, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game.character.plant import AbstractPlant


class PlantCreator:
    """
    植物创建器
    """
    # 禁止直接修改该字段
    plant_registries = {}

    @staticmethod
    def register_plant(name: str):
        def wrapper(plant_cls: Type['AbstractPlant']):
            PlantCreator.plant_registries[name] = plant_cls
            return plant_cls

        return wrapper

    @staticmethod
    def create_plant(name: str) -> 'AbstractPlant':
        if name not in PlantCreator.plant_registries:
            raise Exception('No such Plant!')
        return PlantCreator.plant_registries[name]()

    @staticmethod
    def get_plant_cls(name: str) -> Optional[Type['AbstractPlant']]:
        if name in PlantCreator.plant_registries:
            return PlantCreator.plant_registries[name]
        return None
