from typing import TYPE_CHECKING

from pygame import Vector2

if TYPE_CHECKING:
    from game.level.level_scene import LevelScene
    from game.level.sun import Sun

class SunGenerator:
    """
    阳光生成器, 由LevelScene持有，若LevelScene无该对象，则说明不支持自然生成阳光
    """
    def __init__(self, level: 'LevelScene'):
        self.level = level

    def gen_sun_at_random_pos(self) -> 'Sun':
        """
        在随机位置生成阳光
        :return: 生成的阳光对象
        """
        from game.level.sun import Sun
        sun = Sun.at_random_pos()
        sun.setup_sprite(self.level)
        return sun

    def gen_sun_at(self, pos: Vector2) -> 'Sun':
        """
        在指定位置生成阳光
        :param pos: 阳光的生成位置
        :return: 生成的阳光对象
        """
        from game.level.sun import Sun
        sun = Sun([], pos)
        sun.setup_sprite(self.level)
        return sun