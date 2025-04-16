from __future__ import annotations

import os.path
import random
from typing import Union, TYPE_CHECKING, Optional

import pygame
import pygame_gui
from pygame import Surface, Vector2

from base.cameragroup import CameraGroup, CameraAnimator, EaseInOutQuad
from base.config import LAYERS
from base.game_event import StartPlantEvent, EventBus, MouseMotionEvent, StopPlantEvent, WillGenZombieEvent, \
    ButtonClickEvent
from base.game_grid import PlantGrid, PlantCellFactory
from base.scene import AbstractScene, SceneManager
from base.sprite.game_sprite import GameSprite
from base.sprite.static_sprite import StaticSprite
from game.level.state_machine import StateMachine, State
from game.level.zombie_wave_scheduler import ZombieWaveScheduler
from game.ui.plant_select_container import PlantSelectContainer
from utils.utils import create_ui_manager_with_theme, get_mouse_world_pos

if TYPE_CHECKING:
    from game.character.bullets import Bullet
    from game.character.plant import AbstractPlant
    from game.character.zombie import AbstractZombie

from game.level.scene_config import GenericLevelConfig, PlantCellData

class PlantingState:
    """
    种植状态管理类
    """
    def __init__(self):
        self.plant: Union[AbstractPlant, None] = None
        self.preview_sprite: Union[GameSprite, None] = None
        self.is_planting = False

    def start(self, plant: 'AbstractPlant'):
        self.plant = plant
        self.preview_sprite = StaticSprite([],plant.get_preview_image(),pygame.Vector2(0,0))
        self.preview_sprite.z = LAYERS['highlight']
        self.is_planting = True

    def setup_preview(self, group: pygame.sprite.Group, position: pygame.Vector2):
        self.preview_sprite.group = group
        self.preview_sprite.set_position(position)

    def stop(self):
        self.plant = None
        self.preview_sprite = None
        self.is_planting = False

    def get_plant(self) -> Union['AbstractPlant', None]:
        return self.plant

class LevelStateMachine(StateMachine):
    def __init__(self, level: LevelScene):
        super().__init__()
        self.level = level
        # 开始前状态
        self.before_start = State('before_start')
        # 进行中状态
        self.progress = State('progress')
        # 已结束状态
        self.end = State('end')
        # 选择出战植物状态
        self.select_plant = State('select_plant')
        self.add_state(self.before_start, {self.progress.name, self.end.name})
        self.add_state(self.progress, {self.end.name})
        self.add_state(self.end)
        self.add_state(self.select_plant, {'progress'})
        self.set_initial_state('select_plant')


class LevelFlow:
    def __init__(self, level: LevelScene):
        self.level = level
        self.steps = self._build_steps()
        self.current_step = None
        self.is_running = False

    def _build_steps(self):
        """
        将每一步构建成生成器（协程）
        """
        # yield self._empty()
        yield self._move_camera_to_zombie_area()
        yield self._move_camera_back_to_start()



    def start(self):
        self.steps = self._build_steps()  # 重置生成器
        self.current_step = next(self.steps)
        self.current_step.send(None)
        self.is_running = True

    def update(self, dt: float):
        if not self.is_running or not self.current_step:
            return
        try:
            self.current_step.send(dt)
        except StopIteration:
            # 当前步骤完成，进入下一步
            self.current_step = next(self.steps, None)
            if self.current_step:
                self.current_step.send(None)
            if self.current_step is None:
                self.is_running = False  # 所有步骤执行完毕

    def _empty(self):
        yield

    def _move_camera_to_zombie_area(self):
        yield
        self.level.camera.animate_to(Vector2(400, 0))
        timer = 0
        while timer < 4000:
            timer += yield


    def _move_camera_back_to_start(self):
        yield
        self.level.camera.animate_to(Vector2(0, 0))


class LevelScene(AbstractScene):
    def __init__(self, config_path: str, name: str):
        super().__init__(name)
        from game.game import Game
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        # 加载level配置文件
        self.config = GenericLevelConfig(config_path)
        background = pygame.image.load(self.config.background_path).convert_alpha()
        self.position = pygame.math.Vector2((0,0))
        self.camera = CameraGroup()
        self.camera.animator = CameraAnimator(self.camera, 200, EaseInOutQuad())
        self.background = StaticSprite(self.camera, background, self.position)
        self.background.z = LAYERS['background']
        self.camera.add(self.background)
        self._setup_grid(self.camera, self.config.grid_data)
        self.max_row = self.grid.rows
        self.camera.add(self.grid.get_sprites())
        self.plants: list['AbstractPlant'] = []
        self.zombies: list['AbstractZombie'] = []
        self.bullets: list['Bullet'] = []
        # 种植状态
        self.plant_state = PlantingState()
        # 僵尸生成线位置（仅x坐标有效）
        self.zombie_gen_pos = Vector2(400, 0)
        # 关卡状态
        self.level_state = LevelStateMachine(self)
        # 僵尸波次调度器
        self.zombie_scheduler = self._init_scheduler(config_path)

        #  UI控件
        self.plant_select_container: Optional[PlantSelectContainer] = None
        # self.plant_bank: Optional[None] = None

        self.flow = LevelFlow(self)

        self.setup_state()
        self.level_state.set_initial_state('progress')

    def _init_scheduler(self, config_path: str) -> ZombieWaveScheduler:
        scheduler = ZombieWaveScheduler(os.path.join(os.path.dirname(config_path),'timeline.json'))
        def count_alive_zombie() -> int:
            alive_zombies = [z for z in self.zombies if z.health>0]
            return len(alive_zombies)
        scheduler.get_alive_zombie_count = count_alive_zombie
        return scheduler

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        self.camera.draw(screen, bgsurf, special_flags)
        # UI需最后绘制以显示在所有内容之上
        self.ui_manager.draw_ui(screen)

    def update(self, dt: float):
        self.flow.update(dt)
        super().update(dt)
        # 更新单元格
        self.grid.update(dt)
        self.update_zombie_scheduler(dt)
        # 检查游戏是否已胜利
        # if self.zombie_scheduler.get_progress() == 1:
        #
        # 相机必须要后于单元格更新
        self.camera.update(dt)
        self.ui_manager.update(dt)


    def update_zombie_scheduler(self, dt: float):
        """
        更新僵尸波次调度器
        """
        if self.level_state.current_state.name != 'progress': return
        zombie: Optional[AbstractZombie] = self.zombie_scheduler.update_and_gen(dt/1000)
        if zombie is not None:
            self.add_zombie_from_start(zombie, random.randint(0, self.max_row - 1))

    def set_camera(self, camera: 'CameraGroup'):
        # 清空原相机
        self.camera.empty()
        # 将背景图添加到camera
        self.background.group = camera
        self.camera.add(self.background)

    def add(self, *sprite: Union[list[GameSprite], GameSprite]) -> None:
        self.camera.add(sprite)

    def remove(self, sprite: GameSprite):
        self.camera.remove(sprite)

    def add_plant(self, plant: 'AbstractPlant'):
        self.add(plant)
        self.plants.append(plant)

    def add_zombie(self, zombie: 'AbstractZombie', row: int=0):
        self.add(zombie)
        zombie.setup_sprite(self.camera, self, row)
        self.zombies.append(zombie)

    def add_zombie_from_start(self, zombie: 'AbstractZombie', row: int=0):
        """
        新增僵尸，并将其与当前行的第一个单元格置于同一水平线上，横坐标置于最右边单元格的右边
        """
        self.add(zombie)
        cells = self.grid.get_row_of(row)
        first_cell_pos = cells[-1].get_center_pos()
        zombie_pos = zombie.get_center_pos()
        zombie_pos.y = first_cell_pos.y - zombie.zombie_offset.y
        zombie_pos.x = first_cell_pos.x + 100
        zombie.set_center_pos(zombie_pos)
        zombie.setup_sprite(self.camera, self, row)
        self.zombies.append(zombie)

    def add_bullet(self, bullet: 'Bullet'):
        self.add(bullet)
        self.bullets.append(bullet)

    def remove_plant(self, plant: 'AbstractPlant'):
        if plant not in self.plants: return
        self.remove(plant)
        self.plants.remove(plant)

    def remove_zombie(self, zombie: 'AbstractZombie'):
        if zombie not in self.zombies: return
        self.remove(zombie)
        self.zombies.remove(zombie)

    def remove_bullet(self, bullet: 'Bullet'):
        if bullet not in self.bullets: return
        self.remove(bullet)
        self.bullets.remove(bullet)

    def get_zombies(self) -> list['AbstractZombie']:
        return self.zombies[:]

    def get_plants(self) -> list['AbstractPlant']:
        return self.plants[:]

    def get_bullets(self) -> list['Bullet']:
        return self.bullets[:]

    def get_group(self):
        return self.camera

    def _setup_grid(self, group: pygame.sprite.Group, cell_data: list[list[PlantCellData]]):
        """
        加载单元格信息
        :param group: 单元格所属group
        :param cell_data: 单元格数据
        :return:
        """
        rows = len(cell_data)
        columns = len(cell_data[0])
        cell_matrix = []
        for r in range(rows):
            cell_matrix.append([])
            for c in range(columns):
                cell_matrix[r].append(None)

        for _ in cell_data:
            cell: PlantCellData
            for cell in _:
                cell_matrix[cell.row][cell.column] = PlantCellFactory.create_cell(group, cell.cell_type, cell.row, cell.column, cell.position, cell.size)
        self.grid = PlantGrid(group, cell_matrix, self)

    def get_plant_state(self) -> PlantingState:
        return self.plant_state

    def setup_state(self) -> None:
        def on_enter_progress(state: State):
            self.plant_select_container = PlantSelectContainer()
            self.plant_select_container.setup()
        def on_exit_progress(state: State):
            if self.plant_select_container:
                self.plant_select_container.kill()
                self.plant_select_container = None
        self.level_state.progress.on_enter = on_enter_progress
        self.level_state.progress.on_exit = on_exit_progress

    def setup_ui(self, *args, **kwargs) -> None:
        plant_button_rect = pygame.Rect(0, 0, 100, 60)
        plant_button_rect.topright = (0, 0)
        pygame_gui.elements.UIButton(
            relative_rect=plant_button_rect,
            text="豌豆射手",
            manager=self.ui_manager,
            object_id="#start_plant_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        machine_gun_button_rect = pygame.Rect(0, 0, 100, 60)
        machine_gun_button_rect.topright = (-200, 0)
        pygame_gui.elements.UIButton(
            relative_rect=machine_gun_button_rect,
            text="机枪射手",
            manager=self.ui_manager,
            object_id="#start_plant_machine_gun_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        zombie_button_rect = pygame.Rect(0, 0, 100, 60)
        zombie_button_rect.topright = (-100, 0)
        pygame_gui.elements.UIButton(
            relative_rect=zombie_button_rect,
            text="生成僵尸",
            manager=self.ui_manager,
            object_id="#zombie_gen_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        change_level_button_rect = pygame.Rect(0, 0, 100, 60)
        change_level_button_rect.topright = (-300, 0)
        pygame_gui.elements.UIButton(
            relative_rect=change_level_button_rect,
            text='下一关',
            manager=self.ui_manager,
            object_id="#next_level_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        pop_level_button_rect = pygame.Rect(0, 0, 100, 60)
        pop_level_button_rect.topright = (-400, 0)
        pygame_gui.elements.UIButton(
            relative_rect=pop_level_button_rect,
            text='返回',
            manager=self.ui_manager,
            object_id="#pop_level_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        check_zombie_rect = pygame.Rect(0, 0, 100, 60)
        check_zombie_rect.topright = (-500, 0)
        pygame_gui.elements.UIButton(
            relative_rect=check_zombie_rect,
            text='查看僵尸',
            manager=self.ui_manager,
            object_id="#check_zombie_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        iced_pea_shooter_rect = pygame.Rect(0, 0, 100, 60)
        iced_pea_shooter_rect.topright = (-600, 0)
        pygame_gui.elements.UIButton(
            relative_rect=iced_pea_shooter_rect,
            text='寒冰射手',
            manager=self.ui_manager,
            object_id="#start_plant_iced_pea_shooter_button",
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )

    def setup_scene(self, manager: SceneManager) -> None:
        # 订阅事件
        EventBus().subscribe(StartPlantEvent, self._on_plant)
        EventBus().subscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().subscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().subscribe(WillGenZombieEvent, self._on_gen_zombie)
        EventBus().subscribe(ButtonClickEvent, self._on_check_zombie)
        EventBus().subscribe(ButtonClickEvent, self._on_pop_level)
        # self.setup_state()
        self.flow.start()

    def detach_scene(self) -> None:
        EventBus().unsubscribe(StartPlantEvent, self._on_plant)
        EventBus().unsubscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().unsubscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().unsubscribe(WillGenZombieEvent, self._on_gen_zombie)
        EventBus().unsubscribe(ButtonClickEvent, self._on_check_zombie)
        EventBus().unsubscribe(ButtonClickEvent, self._on_pop_level)

    def process_ui_event(self, event) -> None:
        super().process_ui_event(event)
        if self.plant_select_container:
            self.plant_select_container.process_event(event)


    def _on_plant(self, event: StartPlantEvent) -> None:
        if self.plant_state.is_planting: return
        print("通知网格进入种植状态")
        print(f'收到事件的场景名称: {self.name}')
        # 进入种植状态
        self.plant_state.start(event.plant)
        self.grid.start_selecting()
        self.plant_state.setup_preview(self.camera, get_mouse_world_pos(self.camera.world_pos))
        self.add(self.plant_state.preview_sprite)

    def _on_mouse_move(self, event: MouseMotionEvent):
        """
        处于种植状态时，在鼠标位置绘制植物预览图
        :param event:
        :return:
        """
        if self.plant_state.is_planting:
            self.plant_state.preview_sprite.set_position(get_mouse_world_pos(self.camera.world_pos))

    def _on_stop_planting(self, event: StopPlantEvent):
        self.remove(self.plant_state.preview_sprite)
        self.plant_state.stop()

    def _on_gen_zombie(self, event: WillGenZombieEvent):
        self.add_zombie_from_start(event.zombie, event.row)

    def _on_check_zombie(self, event: ButtonClickEvent):
        if '#check_zombie_button' in event.ui_element.object_ids:
            self.camera.animate_to(self.zombie_gen_pos)

    def _on_pop_level(self, event: ButtonClickEvent):
        if '#pop_level_button' in event.ui_element.object_ids:
            SceneManager().pop_scene()



