from game.character.character_config import CharacterConfigManager
from game.character.zombie import ConfigZombie


def gen_normal_zombie() -> ConfigZombie:
    return ConfigZombie(CharacterConfigManager().get_zombie_config('normal_zombie'),[])

def gen_buckethead_zombie() -> ConfigZombie:
    return ConfigZombie(CharacterConfigManager().get_zombie_config('buckethead_zombie.json'), [])

GENERATOR_TABLE = {
    'normal_zombie': gen_normal_zombie,
    'buckethead_zombie.json': gen_buckethead_zombie
}