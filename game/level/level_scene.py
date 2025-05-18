from __future__ import annotations

import os.path
import random
from typing import Union, TYPE_CHECKING, Optional

import pygame
import pygame_gui
from pygame import Surface, Vector2, Color

from base.cameragroup import CameraGroup, CameraAnimator, EaseInOutQuad
from base.config import LAYERS, AVAILABLE_PLANTS, SUN_GEN_INTERVAL_RANGE
from base.game_event import StartPlantEvent, EventBus, MouseMotionEvent, StopPlantEvent, WillGenZombieEvent, \
    ButtonClickEvent
from base.game_grid import PlantGrid, PlantCellFactory
from base.listenable import ListenableValue
from base.scene import AbstractScene, SceneManager
from base.sprite.game_sprite import GameSprite
from base.sprite.static_sprite import StaticSprite
from game.level.flow import FlowController, FlowPart, part_wait
from game.level.state_machine import StateMachine, State
from game.level.sun_generator import SunGenerator
from game.level.zombie_wave_scheduler import ZombieWaveScheduler
from game.text.animated_text import TextAnimator
from game.ui.in_game_plant_selector import InGamePlantSelector
from game.ui.plant_select_container import PlantSelectContainer
from utils.utils import create_ui_manager_with_theme, get_mouse_world_pos

if TYPE_CHECKING:
    from game.character.bullets import Bullet
    from game.character.plant import AbstractPlant
    from game.character.zombie import AbstractZombie
    from game.level.sun import Sun

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
        self.preview_sprite = StaticSprite([], plant.get_preview_image(), pygame.Vector2(0, 0))
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
    """
    状态: before_start(开始前准备状态), progress(进行中), end(结束状态)
    """
    def __init__(self, level: LevelScene):
        super().__init__()
        self.level = level
        # 开始前状态
        self.before_start = State('before_start')
        # 进行中状态
        self.progress = State('progress')
        # 已结束状态
        self.end = State('end')
        self.add_state(self.before_start, {self.progress.name, self.end.name})
        self.add_state(self.progress, {self.end.name})
        self.add_state(self.end)
        self.set_initial_state('before_start')


class LevelScene(AbstractScene):
    def __init__(self, config_path: str, name: str):
        super().__init__(name)
        from game.game import Game
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        # 加载level配置文件
        self.config = GenericLevelConfig(config_path)
        background = pygame.image.load(self.config.background_path).convert_alpha()
        # 初始化场景世界坐标
        self.world_pos = pygame.math.Vector2((0, 0))
        # 初始化相机
        self.camera = CameraGroup()
        self.camera.animator = CameraAnimator(self.camera, 200, EaseInOutQuad())
        # 初始化背景
        self.background = StaticSprite(self.camera, background, self.world_pos)
        self.background.z = LAYERS['background']
        self.camera.add(self.background)
        # 提示文字
        self.tip_texts = {
            'init': "First Day",
            'will_start0': "Ready...",
            'will_start1': "Fight!",
            'many_zombies': "一大波僵尸即将来袭!"
        }
        self.text_animator = TextAnimator(self.camera)
        # 初始化种植单元格
        self._setup_grid(self.camera, self.config.grid_data)
        self.max_row = self.grid.rows
        self.camera.add(self.grid.get_sprites())
        # Level中的各种精灵对象列表
        self.plants: list['AbstractPlant'] = []
        self.zombies: list['AbstractZombie'] = []
        self.bullets: list['Bullet'] = []
        # 阳光对象列表
        self.suns: list['Sun'] = []
        # 种植状态
        self.plant_state = PlantingState()
        # 相机初始位置
        self.camera_init_pos = Vector2(200, 0)
        self.camera.move_to(self.camera_init_pos)
        # 僵尸生成线位置（仅x坐标有效）
        self.zombie_gen_pos = Vector2(400, 0)
        # 关卡状态
        self.level_state = LevelStateMachine(self)
        # 僵尸波次调度器
        self.zombie_scheduler = self._init_scheduler(config_path)
        # 阳光生成器
        self.sun_generator = SunGenerator(self)
        # 场上能存在的最大可收集的阳光数量(正在被收集的阳光不计算在内)
        self.max_collectable_sun_count = 5
        # 阳光生成间隔(ms)，每次生成完一个阳光后该字段会随机取一个值作为下一个生成间隔
        self.sun_gen_interval = random.randint(SUN_GEN_INTERVAL_RANGE[0], SUN_GEN_INTERVAL_RANGE[1])
        # 阳光生成计时器
        self.sun_gen_timer = 0
        #  初始化UI控件
        self._init_ui()
        # 关卡执行流
        self.flow = FlowController(self)
        self._init_flow()
        self.level_state.set_initial_state('before_start')

    def _init_scheduler(self, config_path: str) -> ZombieWaveScheduler:
        scheduler = ZombieWaveScheduler(os.path.join(os.path.dirname(config_path), 'timeline.json'))

        def count_alive_zombie() -> int:
            alive_zombies = [z for z in self.zombies if z.health > 0]
            return len(alive_zombies)

        scheduler.get_alive_zombie_count = count_alive_zombie
        return scheduler

    def _init_flow(self):
        def _show_text():
            yield from part_wait(1000)
            self.text_animator.fade_in_text(self.tip_texts['init'], (450, 300), color=Color(255, 0, 0), font_size=30,
                                            duration=3000, font_path='resources/ui/HouseofTerror Regular.otf',
                                            outline_width=2, camera=self.camera,)

        def _check_zombie():
            yield from part_wait(3000)
            self.camera.animate_to(Vector2(400, 0), duration=1000)

        def _show_plant_selector():
            yield from part_wait(1000)
            self.in_game_selector.visible = True
            self.plant_select_container.visible = True
            # 等待用户选择植物
            self.flow.pause()

        def _close_selector():
            yield
            self.plant_select_container.visible = False

        def _reset_camera():
            yield
            self.camera.animate_to(Vector2(self.camera_init_pos), duration=1000)

        def _show_ready_text():
            yield from part_wait(1000)
            self.text_animator.fade_in_text(self.tip_texts['will_start0'], (450, 300), color=Color(255, 0, 0),
                                            font_size=30, animation_duration=0, duration=1000,
                                            font_path='resources/ui/HouseofTerror Regular.otf',
                                            outline_width=2, camera=self.camera)
            yield from part_wait(1000)
            self.text_animator.fade_in_text(self.tip_texts['will_start1'], (450, 300), color=Color(255, 0, 0),
                                            font_size=30, animation_duration=0, duration=1000,
                                            font_path='resources/ui/HouseofTerror Regular.otf',
                                            outline_width=2, camera=self.camera)

        def _start_level():
            yield from part_wait(1000)
            self.level_state.transition_to('progress')

        self.flow.add_part(FlowPart(_show_text))
        self.flow.add_part(FlowPart(_check_zombie))
        self.flow.add_part(FlowPart(_show_plant_selector))
        self.flow.add_part(FlowPart(_close_selector))
        self.flow.add_part(FlowPart(_reset_camera))
        self.flow.add_part(FlowPart(_show_ready_text))
        self.flow.add_part(FlowPart(_start_level))

    def _init_ui(self):
        self.plant_select_container: Optional[PlantSelectContainer] = PlantSelectContainer.fromFile(AVAILABLE_PLANTS)
        self.in_game_selector = InGamePlantSelector([])
        self.in_game_selector.visible = False
        self.plant_select_container.visible = False

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        self.camera.draw(screen, bgsurf, special_flags)
        self.plant_select_container.draw(screen, bgsurf, special_flags)
        self.in_game_selector.draw(screen)
        # UI需最后绘制以显示在所有内容之上
        self.ui_manager.draw_ui(screen)

    def update(self, dt: float):
        self.flow.update(dt)
        super().update(dt)
        # 更新阳光生成计时器
        if self.can_add_sum():
            self.sun_gen_timer += dt
            if self.sun_gen_timer >= self.sun_gen_interval:
                # 生成阳光
                self.sun_generator.gen_sun_at_random_pos()
                self.sun_gen_timer = 0
                self.sun_gen_interval = random.randint(SUN_GEN_INTERVAL_RANGE[0], SUN_GEN_INTERVAL_RANGE[1])
        # 更新单元格
        self.grid.update(dt)
        self.update_zombie_scheduler(dt)
        # 检查游戏是否已胜利
        # if self.zombie_scheduler.get_progress() == 1:
        #
        self.text_animator.update(dt)
        # 相机必须要后于单元格更新
        self.camera.update(dt)

        self.plant_select_container.update(dt)
        self.in_game_selector.update(dt)
        self.ui_manager.update(dt)

    def update_zombie_scheduler(self, dt: float):
        """
        更新僵尸波次调度器
        """
        if self.level_state.current_state.name != 'progress': return
        zombie: Optional[AbstractZombie] = self.zombie_scheduler.update_and_gen(dt / 1000)
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

    def add_zombie(self, zombie: 'AbstractZombie', row: int = 0):
        self.add(zombie)
        zombie.setup_sprite(self.camera, self, row)
        self.zombies.append(zombie)

    def add_zombie_from_start(self, zombie: 'AbstractZombie', row: int = 0):
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

    def add_sun(self, sun: 'Sun'):
        if sun not in self.suns:
            self.add(sun)
            self.suns.append(sun)

    def remove_sun(self, sun: 'Sun'):
        if sun not in self.suns: return
        self.remove(sun)
        self.suns.remove(sun)

    def can_add_sum(self):
        """
        当前是否能添加阳光, 在添加阳光前请务必调用此方法
        """
        # 统计未被收集的阳光数
        count = 0
        for sun in self.suns:
            if not sun.collecting:
                count += 1
        if count >= self.max_collectable_sun_count:
            return False
        return True

    def get_zombies(self) -> list['AbstractZombie']:
        return self.zombies[:]

    def get_plants(self) -> list['AbstractPlant']:
        return self.plants[:]

    def get_bullets(self) -> list['Bullet']:
        return self.bullets[:]

    def get_suns(self) -> list['Sun']:
        return self.suns

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
                cell_matrix[cell.row][cell.column] = PlantCellFactory.create_cell(group, cell.cell_type, cell.row,
                                                                                  cell.column, cell.position, cell.size)
        self.grid = PlantGrid(group, cell_matrix, self)

    def get_plant_state(self) -> PlantingState:
        return self.plant_state

    def setup_ui(self, *args, **kwargs) -> None:
        pop_level_button_rect = pygame.Rect(0, 0, 100, 60)
        pop_level_button_rect.topright = (0, 0)
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
        # 这俩的setup方法中有事件订阅, 需要在detach_scene中调用destroy方法取消订阅
        self.plant_select_container.setup()
        self.in_game_selector.setup()

    def setup_scene(self, manager: SceneManager) -> None:
        super().setup_scene(manager)
        # self.setup_state()
        self.flow.start()

    def mount(self):
        # 订阅事件
        EventBus().subscribe(StartPlantEvent, self._on_plant)
        EventBus().subscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().subscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().subscribe(ButtonClickEvent, self._on_pop_level)
        EventBus().subscribe(ButtonClickEvent, self._on_start_fight)

    def unmount(self):
        EventBus().unsubscribe(StartPlantEvent, self._on_plant)
        EventBus().unsubscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().unsubscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().unsubscribe(ButtonClickEvent, self._on_pop_level)
        EventBus().unsubscribe(ButtonClickEvent, self._on_start_fight)
        self.plant_select_container.unmount()
        self.in_game_selector.unmount()
        self.grid.unmount()
        all_sprite = [self.plants, self.zombies, self.suns]
        for lis in all_sprite:
            for spr in lis:
                spr.unmount()

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

    def _on_pop_level(self, event: ButtonClickEvent):
        if '#pop_level_button' in event.ui_element.object_ids:
            SceneManager().pop_scene()

    def _on_start_fight(self, event: ButtonClickEvent):
        if '#start_fight_button' in event.ui_element.object_ids:
            print("开始战斗")
            # 恢复关卡流执行
            self.flow.resume()
            from base.game_event import EventBus, StartFightEvent
            # 发布关卡开始事件
            EventBus().publish(StartFightEvent())
