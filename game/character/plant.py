import abc

from base.game_grid import AbstractPlantCell, GroundedPlantCell, WaterPlantCell


class AbstractPlant(abc.ABC):
    def __init__(self, cell: AbstractPlantCell):
        self.cell = cell

class GroundedPlant(AbstractPlant):
    def __init__(self, cell: GroundedPlantCell):
        AbstractPlant.__init__(self, cell)

class WaterPlant(AbstractPlant):
    def __init__(self, cell: WaterPlantCell):
        AbstractPlant.__init__(self, cell)