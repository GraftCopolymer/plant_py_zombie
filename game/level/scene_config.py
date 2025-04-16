import os.path

import pygame
from pytmx import load_pygame, TiledObject, TiledImageLayer

from game.character import Position


class PlantCellData:
    def __init__(self, position: Position, size: pygame.Vector2, row: int, column: int, cell_type: str):
        self.position = position
        self.size = size
        self.row = row
        self.column = column
        self.cell_type = cell_type

class GenericLevelConfig:
    def __init__(self, config_path: str):
        self.path = config_path
        self.grid_data: list[list[PlantCellData]] = []
        # 背景路径
        self.background_path: str = ''
        self.parse(config_path)

    def parse(self, path: str) -> None:
        tmx_data = load_pygame(path)
        data: list[list] = []

        for layer in tmx_data.layers:
            if layer.name == 'Background':
                self.background_path = os.path.join(os.path.dirname(path), layer.source)

        for layer in tmx_data.objectgroups:
            if layer.name == 'Plantable':
                # 行数
                rows = layer.properties.get("rows")
                # 列数
                columns = layer.properties.get("columns")
                for r in range(rows):
                    data.append([])
                    for c in range(columns):
                        data[r].append(None)
                # 读取单元格
                obj: TiledObject
                for obj in layer:
                    row_n: int = obj.properties.get("row")
                    column_n: int = obj.properties.get("column")
                    cell_type = obj.properties.get("cell_type")
                    data[row_n][column_n] = PlantCellData(pygame.Vector2(obj.x, obj.y), pygame.Vector2(obj.width, obj.height),row_n, column_n, cell_type)
        self.grid_data = data
