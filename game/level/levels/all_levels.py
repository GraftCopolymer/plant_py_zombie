from game.level.level_creator import LevelCreator
from game.level.level_scene import LevelScene


@LevelCreator.register_level('first_level')
class FirstDayLevel(LevelScene):
    """
    第一关，没什么特别的
    """
    def __init__(self):
        super().__init__('./resources/level/first_day/first_day.tmx', 'first_day')

@LevelCreator.register_level('night_level')
class NightLevel(LevelScene):
    """
    夜晚关卡
    """
    def __init__(self):
        super().__init__('./resources/level/night_level/night_level.tmx', 'night_level')
        self.tip_texts = {
            'init': "Night is coming...",
            'will_start0': "Ready...",
            'will_start1': "Fight!",
        }
        self.is_night = True

    def can_naturally_gen_sum(self):
        """
        不允许自然生成阳光
        """
        return False
