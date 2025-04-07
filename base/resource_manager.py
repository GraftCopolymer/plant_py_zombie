import os
import threading

from game.character.character_config import ConfigManager

class ResourceLoader:
    """
    资源加载器，单例
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def load_zombie(self, zombie_path: str) -> None:
        """
        加载僵尸资源
        :return: None
        """
        for directory in os.listdir(zombie_path):
            directory_path = os.path.join(zombie_path, directory)
            if not os.path.isdir(directory_path):
                continue  # 跳过非目录

            target_name = "{}.json".format(directory)
            json_path = os.path.join(directory_path, target_name)

            if not os.path.isfile(json_path):
                continue  # 跳过不包含对应文件夹名称的json文件的文件夹

            ConfigManager().load('zombie', json_path)

    def load_plant(self) -> None:
        """
        加载植物 TODO
        :return: None
        """
        pass

