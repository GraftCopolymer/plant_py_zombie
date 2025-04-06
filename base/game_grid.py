from __future__ import annotations

import abc
from typing import Union

import pygame.sprite
from pygame import SurfaceType

from base.sprite.game_sprite import GameSprite

from game.character import  Position

class SceneGrid:
    def __init__(self, row_height: int, column_width: int, cells: list[list[Union[GridCell, None]]]):
        assert len(cells) > 0
        assert len(cells[0]) > 0
        assert row_height > 0
        assert column_width > 0
        self.grid_data = cells
        self.rows = len(cells)
        self.column = len(cells[0])
        self.row_height = row_height
        self.column_width = column_width
        self.group = pygame.sprite.Group()
        # TODO: 整理单元格坐标和尺寸

    @classmethod
    def empty_grid(cls, rows: int, columns: int, row_height: int, column_width: int):
        assert rows > 0
        assert columns > 0
        cells: list[list[Union[GridCell, None]]] = []
        for row in range(rows):
            cells.append([])
            for column in range(columns):
                cells[row].append(None)
        return cls(row_height, column_width, cells)

    def place_plant(self, row: int, column: int) -> bool:
        pass

    def update(self, dt: float):
        self.group.update()

    def is_empty(self, row: int, column: int):
        return self.grid_data[row][column] is None


class GridCell(GameSprite, abc.ABC):
    """
    抽象单元格
    """
    def __init__(self, group: pygame.sprite.Group, grid: SceneGrid, row: int, column: int, position: Position):
        GameSprite.__init__(self, group, position)
        self.grid = grid
        self.row = row
        self.column = column

class AbstractPlantCell(GridCell, abc.ABC):
    # TODO: 编写植物类型
    def __init__(self, group: pygame.sprite.Group, plants: list, grid: SceneGrid, row: int, column: int, position: Position):
        GridCell.__init__(self, group, grid, row, column, position)
        self.plants = plants

class GroundedPlantCell(AbstractPlantCell):
    def __init__(self, group: pygame.sprite.Group, plants: list, grid: SceneGrid, row: int, column: int, position: Position):
        AbstractPlantCell.__init__(self, group, plants, grid, row, column, position)
        # TODO: 限制植物为陆地植物

    def update(self, dt: float) -> None:
        pass

class WaterPlantCell(AbstractPlantCell):
    def __init__(self, group: pygame.sprite.Group, plants: list, grid, row, column, position: Position):
        AbstractPlantCell.__init__(self, group, plants, grid, row, column, position)
        # TODO: 限制植物为水生植物

    def update(self, dt: float) -> None:
        pass
