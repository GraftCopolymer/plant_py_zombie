from __future__ import annotations

import os.path
import random
from typing import Union, TYPE_CHECKING, Optional

import pygame
import pygame_gui
from pygame import Surface, Vector2, Color

from base.cameragroup import CameraGroup, CameraAnimator, EaseInOutQuad
from base.config import LAYERS, AVAILABLE_PLANTS, SUN_GEN_INTERVAL_RANGE
from base.game_event import KeyDownEvent
from base.game_event import StartPlantEvent, EventBus, MouseMotionEvent, StopPlantEvent, \
    ButtonClickEvent, EndShovelingEvent
from base.game_event import StartShovelingEvent
from base.game_grid import PlantGrid, PlantCellFactory
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
from game.ui.result_dialog import ResultDialog
from game.ui.shovel import ShovelSlot, Shovel
from utils.utils import create_ui_manager_with_theme, get_mouse_world_pos

if TYPE_CHECKING:
    from game.character.bullets import Bullet
    from game.character.plant import AbstractPlant
    from game.character.zombie import AbstractZombie
    from game.level.sun import Sun

from game.level.scene_config import GenericLevelConfig, PlantCellData

class InteractionStateMachine(StateMachine):
    def __init__(self):
        super().__init__()
        self.planting = State('planting')
        self.shoveling = State('shoveling')
        self.normal = State('normal')

        self.add_state(self.normal, {'planting', 'shoveling'})
        self.add_state(self.planting, {'normal'})
        self.add_state(self.shoveling, {'normal'})
        self.set_initial_state('normal')

class InteractionState:
    """
    关卡交互状态类
    """
    def __init__(self):
        # 处于种植状态时, 此处储存即将种植的植物对象
        self.plant: Union[AbstractPlant, None] = None
        # 跟随鼠标运动的预览精灵图
        self.preview_sprite: Union[GameSprite, None] = None
        # 交互状态机
        self.state_machine = InteractionStateMachine()

    def start_planting(self, plant: 'AbstractPlant'):
        if self.state_machine.can_transition_to('planting'):
            self.plant = plant
            self.preview_sprite = StaticSprite([], plant.get_preview_image(), pygame.Vector2(0, 0))
            self.preview_sprite.z = LAYERS['highlight']
            self.state_machine.transition_to('planting')

    def stop_planting(self):
        if self.state_machine.can_transition_to('normal'):
            self.plant = None
            self.preview_sprite = None
            self.state_machine.transition_to('normal')

    def start_shoveling(self):
        if self.state_machine.can_transition_to('shoveling'):
            self.preview_sprite = Shovel([])
            self.preview_sprite.z = LAYERS['highlight']
            self.state_machine.transition_to('shoveling')

    def stop_shoveling(self):
        if self.state_machine.can_transition_to('normal'):
            self.plant = None
            self.preview_sprite = None
            self.state_machine.transition_to('normal')

    def is_planting(self):
        return self.state_machine.get_state() == 'planting'

    def is_shoveling(self):
        return self.state_machine.get_state() == 'shoveling'

    def can_planting(self):
        return self.state_machine.can_transition_to('planting')

    def can_shoveling(self):
        return self.state_machine.can_transition_to('shoveling')

    def can_normal(self):
        return self.state_machine.can_transition_to('normal')

    def setup_preview(self, group: pygame.sprite.Group, position: pygame.Vector2):
        self.preview_sprite.group = group
        self.preview_sprite.set_position(position)

    def get_plant(self) -> Union['AbstractPlant', None]:
        return self.plant


class LevelStateMachine(StateMachine):
    """
    状态: before_start(开始前准备状态), progress(进行中), end(结束状态)
    """
    def __init__(self):
        super().__init__()
        # 开始前状态
        self.before_start = State('before_start')
        # 进行中状态
        self.progress = State('progress')
        # 胜利
        self.win = State('win')
        # 失败
        self.fail = State('fail')
        self.add_state(self.before_start, {'progress'})
        self.add_state(self.progress, {'win','fail'})
        self.add_state(self.win)
        self.add_state(self.fail)
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
        # 相机初始位置
        self.camera_init_pos = Vector2(100, 0)
        self.camera.move_to(self.camera_init_pos)
        # 僵尸生成线位置（仅x坐标有效）
        self.zombie_gen_pos = Vector2(400, 0)
        # 僵尸胜利线位置, 当有僵尸到达此位置后, 游戏将失败(仅x坐标有效)
        self.zombie_win_line = Vector2(50, 0)
        # 关卡状态
        self.level_state = LevelStateMachine()
        # 关卡交互状态
        self.interaction_state = InteractionState()
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
            # 暂停执行流，等待关卡结果(失败或胜利)
            self.flow.pause()

        self.flow.add_part(FlowPart(_show_text))
        self.flow.add_part(FlowPart(_check_zombie))
        self.flow.add_part(FlowPart(_show_plant_selector))
        self.flow.add_part(FlowPart(_close_selector))
        self.flow.add_part(FlowPart(_reset_camera))
        self.flow.add_part(FlowPart(_show_ready_text))
        self.flow.add_part(FlowPart(_start_level))

    def _init_ui(self):
        # 出战植物选择
        self.plant_select_container: Optional[PlantSelectContainer] = PlantSelectContainer.fromFile(AVAILABLE_PLANTS)
        # 游戏内植物选择器
        self.in_game_selector = InGamePlantSelector([])
        # 铲子插槽
        self.shovel_slot = ShovelSlot()
        # 游戏结算对话框
        self.result_dialog = ResultDialog(self)
        self.in_game_selector.visible = False
        self.plant_select_container.visible = False
        self.result_dialog.visible = False

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        self.camera.draw(screen, bgsurf, special_flags)
        self.plant_select_container.draw(screen)
        self.in_game_selector.draw(screen)
        self.shovel_slot.draw(screen)
        self.result_dialog.draw(screen)
        # UI需最后绘制以显示在所有内容之上
        self.ui_manager.draw_ui(screen)

    def update(self, dt: float):
        super().update(dt)
        # 检查游戏状态(进行中、胜利、失败)
        self.check_level_result()
        # 游戏已结束，不再更新level, 但仍更新对话框, 否则用户看不到对话框弹出
        self.flow.update(dt)
        self.result_dialog.update(dt)
        if self.level_state.get_state() == 'win' or self.level_state.get_state() =='fail': return
        # 更新阳光生成计时器
        if self.can_naturally_gen_sum():
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
        self.shovel_slot.update(dt)
        self.ui_manager.update(dt)

    def update_zombie_scheduler(self, dt: float):
        """
        更新僵尸波次调度器
        """
        if self.level_state.current_state.name != 'progress': return
        zombie: Optional[AbstractZombie] = self.zombie_scheduler.update_and_gen(dt)
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

    def check_level_result(self):
        """
        检测游戏是否结束, 并根据游戏结果更新状态
        """
        # 检测游戏是否已胜利
        if self.zombie_scheduler.get_progress() >= 1 and len(self.zombies) == 0 and self.level_state.can_transition_to('win'):
            self.level_state.transition_to('win')
            # 添加胜利流并执行
            self.flow.add_part(FlowPart(self._flow_win))
            self.flow.resume()
        elif self.level_state.can_transition_to('fail'):
            # 检测是否有僵尸到达僵尸胜利线
            for z in self.zombies:
                if z.world_pos.x <= self.zombie_win_line.x:
                    self.level_state.transition_to('fail')
                    # 添加失败流并执行
                    self.flow.add_part(FlowPart(self._flow_fail))
                    self.flow.resume()
                    break

    def can_naturally_gen_sum(self):
        """
        当前能否自然生成阳光
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

    def get_interaction_state(self) -> InteractionState:
        return self.interaction_state

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
        # show_win_dialog_button_rect = pygame.Rect(0, 0, 100, 60)
        # show_win_dialog_button_rect.topright = (0, 70)
        # pygame_gui.elements.UIButton(
        #     relative_rect=show_win_dialog_button_rect,
        #     text='显示胜利对话框',
        #     manager=self.ui_manager,
        #     object_id="#show_win_dialog_button",
        #     anchors={
        #         'right': 'right',
        #         'top': 'top'
        #     }
        # )
        # 这俩的setup方法中有事件订阅, 需要在detach_scene中调用destroy方法取消订阅
        self.plant_select_container.setup()
        self.in_game_selector.setup()
        self.shovel_slot.setup(self)
        self.result_dialog.setup()

    def setup_scene(self, manager: SceneManager) -> None:
        super().setup_scene(manager)
        # self.setup_state()
        self.flow.start()

    def mount(self):
        # 订阅事件
        EventBus().subscribe(StartPlantEvent, self._on_plant)
        EventBus().subscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().subscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().subscribe(ButtonClickEvent, self._on_button_clicked)
        EventBus().subscribe(ButtonClickEvent, self._on_start_fight)
        EventBus().subscribe(StartShovelingEvent, self._on_shoveling)
        EventBus().subscribe(EndShovelingEvent, self._on_stop_shoveling)
        EventBus().subscribe(KeyDownEvent, self._on_key_pressed)

    def unmount(self):
        EventBus().unsubscribe(StartPlantEvent, self._on_plant)
        EventBus().unsubscribe(MouseMotionEvent, self._on_mouse_move)
        EventBus().unsubscribe(StopPlantEvent, self._on_stop_planting)
        EventBus().unsubscribe(ButtonClickEvent, self._on_button_clicked)
        EventBus().unsubscribe(ButtonClickEvent, self._on_start_fight)
        EventBus().unsubscribe(StartShovelingEvent, self._on_shoveling)
        EventBus().unsubscribe(EndShovelingEvent, self._on_stop_shoveling)
        EventBus().unsubscribe(KeyDownEvent, self._on_key_pressed)
        self.plant_select_container.unmount()
        self.in_game_selector.unmount()
        self.shovel_slot.unmount()
        self.grid.unmount()
        all_sprite = [self.plants, self.zombies, self.suns]
        for lis in all_sprite:
            for spr in lis:
                spr.unmount()

    def detach_scene(self):
        # 单独结束对话框的事件
        self.result_dialog.unmount()
        super().detach_scene()

    def process_ui_event(self, event) -> None:
        super().process_ui_event(event)
        if self.plant_select_container is not None:
            self.plant_select_container.process_event(event)
        if self.result_dialog is not None:
            self.result_dialog.process_event(event)

    def _on_plant(self, event: StartPlantEvent) -> None:
        if not self.interaction_state.can_planting(): return
        print("通知网格进入种植状态")
        print(f'收到事件的场景名称: {self.name}')
        # 进入种植状态
        self.interaction_state.start_planting(event.plant)
        self.grid.start_selecting()
        self.interaction_state.setup_preview(self.camera, get_mouse_world_pos(self.camera.world_pos))
        self.add(self.interaction_state.preview_sprite)

    def _on_shoveling(self, event: 'StartShovelingEvent'):
        if not self.interaction_state.can_shoveling(): return
        print("进入铲植物状态")
        self.interaction_state.start_shoveling()
        self.grid.start_selecting()
        self.interaction_state.setup_preview(self.camera, get_mouse_world_pos(self.camera.world_pos) - Vector2(0, self.interaction_state.preview_sprite.rect.height))
        self.add(self.interaction_state.preview_sprite)

    def _on_mouse_move(self, event: MouseMotionEvent):
        """
        处于种植状态时，在鼠标位置绘制植物预览图
        :param event:
        :return:
        """
        if self.interaction_state.is_planting():
            self.interaction_state.preview_sprite.set_position(get_mouse_world_pos(self.camera.world_pos))
        elif self.interaction_state.is_shoveling():
            self.interaction_state.preview_sprite.set_position(get_mouse_world_pos(self.camera.world_pos) - Vector2(0, self.interaction_state.preview_sprite.rect.height))

    def _on_stop_planting(self, event: StopPlantEvent):
        self.remove(self.interaction_state.preview_sprite)
        self.interaction_state.stop_planting()

    def _on_stop_shoveling(self, event: EndShovelingEvent):
        self.remove(self.interaction_state.preview_sprite)
        self.interaction_state.stop_shoveling()
        self.grid.stop_selecting()

    def _on_key_pressed(self, event: 'KeyDownEvent') -> None:
        if event.key != pygame.K_ESCAPE: return
        # 按下esc时停止种植或铲植物
        if self.interaction_state.is_shoveling():
            self.remove(self.interaction_state.preview_sprite)
            self.interaction_state.stop_shoveling()
            self.grid.stop_selecting()
            EventBus().publish(EndShovelingEvent())
            event.mark_handled()
        elif self.interaction_state.is_planting():
            self.remove(self.interaction_state.preview_sprite)
            self.interaction_state.stop_planting()
            self.grid.stop_planting()
            event.mark_handled()

    def _on_button_clicked(self, event: ButtonClickEvent):
        if '#pop_level_button' in event.ui_element.object_ids:
            SceneManager().pop_scene()
        elif '#show_win_dialog_button' in event.ui_element.object_ids:
            self.result_dialog.show('fail')

    def _on_start_fight(self, event: ButtonClickEvent):
        if '#start_fight_button' in event.ui_element.object_ids:
            print("开始战斗")
            # 恢复关卡流执行
            self.flow.resume()
            from base.game_event import EventBus, StartFightEvent
            # 发布关卡开始事件
            EventBus().publish(StartFightEvent())

    def _flow_win(self):
        """
        游戏胜利将执行的流
        """
        yield
        self.result_dialog.show('win')
    def _flow_fail(self):
        """
        游戏失败将执行的流
        """
        yield
        self.result_dialog.show('fail')

