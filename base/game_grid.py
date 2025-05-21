from __future__ import annotations

import abc
import enum
from abc import abstractmethod
from typing import Union, TYPE_CHECKING, Optional

import pygame.sprite

from base.config import LAYERS

if TYPE_CHECKING:
    from game.character.plant import AbstractPlant
    from game.level.level_scene import LevelScene

from base.game_event import MouseMotionEvent, EventBus, ClickEvent, StopPlantEvent
from base.sprite.game_sprite import GameSprite
from base.sprite.static_sprite import StaticSprite

from game.character import  Position


class PlantCellStatus(enum.Enum):
    CAN_PLANT = 'can_plant'
    CAN_REMOVE = 'can_remove'
    NORMAL = 'normal'

class PlantGridStatus(enum.Enum):
    NORMAL = 'normal'
    SELECTING = 'selecting'

class PlantGrid:
    """
    请勿尝试在运行时修改本类的对象信息，该类对象在运行时被视作不变，尝试修改可能会出现问题
    """
    def __init__(self, group: pygame.sprite.Group, cells: list[list[AbstractPlantCell]], level: Union[LevelScene, None]=None):
        assert len(cells) > 0
        assert len(cells[0]) > 0
        self.grid_data = cells
        self.rows = len(cells)
        self.columns = len(cells[0])
        self.group = group
        self.level = level
        # 种植相关
        self.grid_status = PlantGridStatus.NORMAL
        self.selected_cell: Union[AbstractPlantCell, None] = None
        assert self._check_grid_validation()

        EventBus().subscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().subscribe(ClickEvent, self._on_mouse_click)

    def _on_mouse_move(self, event: 'MouseMotionEvent') -> None:
        if self.grid_status == PlantGridStatus.SELECTING:
            target_cell: Union[AbstractPlantCell, None] = None
            index = 0
            cells = self.get_cells()
            while index < len(cells):
                if cells[index].rect.collidepoint(event.get_world_pos(self.level.camera.world_pos) + cells[index].highlight_mask.rect_offset):
                    target_cell = cells[index]
                    self.cancel_all_highlight()
                    self.highlight_row(target_cell.row)
                    self.highlight_column(target_cell.column)
                    break
                index += 1
            if not target_cell: self.cancel_all_highlight()
            self.selected_cell = target_cell

    def _on_mouse_click(self, event: ClickEvent):
        if self.grid_status == PlantGridStatus.SELECTING and self.selected_cell is not None:
            if self.level.get_interaction_state().is_planting():
                plant = self.level.get_interaction_state().get_plant()
                if plant is not None:
                    self.place_plant(self.selected_cell, plant)
                    self.stop_planting()
            elif self.level.get_interaction_state().is_shoveling():
                self.shovel_plant(self.selected_cell)

    def place_plant(self, cell: AbstractPlantCell, plant: AbstractPlant) -> None:
        print("放置植物")
        cell.slot.append(plant)
        plant.setup_sprite(self.group, cell, self.level)

    def shovel_plant(self, cell: AbstractPlantCell, only_top=True) -> Optional[AbstractPlant]:
        print("铲除植物")
        plants = cell.slot[:]
        if len(plants) == 0: return None
        plants.sort(key=lambda pl: pl.z)
        target: AbstractPlant = plants[-1]
        cell.slot.remove(target)
        self.level.remove_plant(target)
        return target

    def stop_planting(self):
        print("停止种植")
        # 触发结束种植事件
        EventBus().publish(StopPlantEvent(self.level.get_interaction_state().plant, self.selected_cell))
        self.selected_cell = None
        self.grid_status = PlantGridStatus.NORMAL
        self.cancel_all_highlight()

    def start_selecting(self):
        print("网格开始选择种植单元格")
        self.grid_status = PlantGridStatus.SELECTING

    def stop_selecting(self):
        self.grid_status = PlantGridStatus.NORMAL
        self.cancel_all_highlight()

    def update(self, dt: float):
        for row in self.grid_data:
            for cell in row:
                cell.update(dt)

    def get_sprites(self):
        """
        :return: 所有单元格中的所有sprite
        """
        res: list[GameSprite] = []
        for row in self.grid_data:
            for cell in row:
                res.extend(cell.get_sprites())
        return res

    def get_cells(self) -> list[AbstractPlantCell]:
        """
        :return: 所有单元格对象
        """
        res = []
        for _ in self.grid_data:
            for cell in _:
                res.append(cell)
        return res


    def is_empty(self, row: int, column: int) -> bool:
        """
        :param row: 目标单元格行数
        :param column: 目标单元格列数
        :return: bool值，该单元格的slot中是否存有对象
        """
        return self.grid_data[row][column].is_empty()

    def _check_grid_validation(self) -> bool:
        """
        检查cell数据是否合法
        需满足每行cell的x坐标递增的顺序
        :return:
        """
        row_num = 0
        while row_num < len(self.grid_data):
            column_num = 0
            row = self.grid_data[row_num]
            while column_num < len(row) - 1:
                if row[column_num].position.x >= row[column_num + 1].position.x:
                    return False
                column_num += 1
            row_num += 1
        return True


    def get_row_of(self, row: int) -> list[AbstractPlantCell]:
        assert 0 <= row < len(self.grid_data)
        return self.grid_data[row][:]

    def get_column_of(self, column: int) -> list[AbstractPlantCell]:
        index = 0
        res = []
        while index < len(self.grid_data):
            res.append(self.grid_data[index][column])
            index += 1
        return res

    def get_slot_of(self, row: int, column: int) -> list[GameSprite]:
        """
        :param row: 目标单元格行数
        :param column: 目标单元格列数
        :return: 目标单元格的slot中存放的对象
        """
        return self.grid_data[row][column].get_sprites()

    def highlight(self, row: int, column: int) -> None:
        self.grid_data[row][column].highlight()

    def cancel_highlight(self, row: int, column: int) -> None:
        self.grid_data[row][column].cancel_highlight()

    def highlight_row(self, row: int) -> None:
        for c in range(self.columns):
            self.highlight(row, c)

    def highlight_column(self, column: int) -> None:
        for r in range(self.rows):
            self.highlight(r, column)

    def cancel_highlight_row(self, row: int) -> None:
        for c in range(self.columns):
            self.cancel_highlight(row, c)

    def cancel_highlight_column(self, column: int) -> None:
        for r in range(self.rows):
            self.cancel_highlight(r, column)

    def cancel_all_highlight(self):
        for _ in self.grid_data:
            for cell in _:
                cell.cancel_highlight()

    def unmount(self):
        EventBus().unsubscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().unsubscribe(ClickEvent, self._on_mouse_click)


class GridCell(abc.ABC):
    """
    抽象单元格
    """
    def __init__(self, row: int, column: int, size: pygame.Vector2, position: Position):
        self.row = row
        self.column = column
        self.position = position
        self.rect = pygame.Rect(0,0,*size)
        self.rect.topleft = (self.position.x, self.position.y)

    def set_position(self, new_pos: Position):
        self.position = new_pos
        self.rect.topleft = (self.position.x, self.position.y)


    @abstractmethod
    def update(self, dt: float) -> None: pass


class AbstractPlantCell(GridCell, abc.ABC):
    # TODO: 编写植物类型
    highlight_count = 0
    def __init__(self, group: pygame.sprite.Group, plants: list, row: int, column: int, size: pygame.Vector2, position: Position):
        GridCell.__init__(self, row, column, size, position)
        self.group = group
        self.plants = plants
        # 高亮遮罩
        self.highlight_mask = StaticSprite(group, pygame.Surface(size).convert_alpha(), position)
        self.highlight_mask.display = False
        self.highlight_mask.z = LAYERS['highlight']
        # 半透明白色
        self.highlight_mask.image.fill((255, 255, 255, 100))
        self.debug_point_pos = self.get_center_pos()
        # 单元格槽位，一个列表，其中的对象将被重叠显示，受对象的图层影响
        self.slot: list[AbstractPlant] = []

        # self.rect_sprite = StaticSprite(group, pygame.Surface(self.rect.size), self.position.copy())
        # center_dot = StaticSprite(group, pygame.Surface((10,10)),self.get_center_pos())
        # self.slot.append(center_dot)
        # self.slot.append(self.rect_sprite)
        self.cell_status: PlantCellStatus = PlantCellStatus.CAN_PLANT

    def set_position(self, new_pos: Position):
        super().set_position(new_pos.copy())
        # 移动slot中的对象
        for sprite in self.slot:
            sprite.set_position(new_pos)

    def update(self, dt: float) -> None:
        for sprite in self.slot:
            sprite.update(dt)

    def highlight(self) -> None:
        """
        高亮本单元格
        :return:
        """
        self.highlight_mask.display = True

    def cancel_highlight(self):
        """
        取消本单元格高亮
        :return:
        """
        self.highlight_mask.display = False

    def get_sprites(self) -> list[GameSprite]:
        """
        :return: self.slot
        """
        return self.slot[:]

    def is_empty(self):
        return len(self.slot) == 0

    def get_center_pos(self) -> pygame.Vector2:
        return pygame.Vector2(self.rect.center)


class GrassPlantCell(AbstractPlantCell):
    def __init__(self, group: pygame.sprite.Group, plants: list, row: int, column: int, size: pygame.Vector2, position: Position):
        AbstractPlantCell.__init__(self, group, plants, row, column, size, position)
        # TODO: 限制植物为陆地植物

    def update(self, dt: float) -> None:
        pass

class WaterPlantCell(AbstractPlantCell):
    def __init__(self, group: pygame.sprite.Group, plants: list, row, column, size: pygame.Vector2, position: Position):
        AbstractPlantCell.__init__(self, group, plants, row, column, size, position)
        # TODO: 限制植物为水生植物

    def update(self, dt: float) -> None:
        pass

class CellType(enum.Enum):
    GRASS = 'grass'
    WATER = 'water'
    DIRT = 'dirt'
    GROUND = 'ground'

class PlantCellFactory:
    @staticmethod
    def create_cell(group: pygame.sprite.Group, cell_type: str, row: int, column: int, position: pygame.Vector2, size: pygame.Vector2) -> AbstractPlantCell:
        if cell_type == CellType.GRASS.value:
            return GrassPlantCell(group, [], row, column, size, position)
        if cell_type == CellType.WATER.value:
            return WaterPlantCell(group, [], row, column, size, position)
        else:
            raise Exception('Unsupported cell type')