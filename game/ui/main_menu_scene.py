import pygame.image
from pygame import Surface, Vector2
from pygame.rect import Rect
from pygame_gui.elements import UIButton

from base.game_event import ButtonClickEvent, EventBus
from base.scene import AbstractScene, SceneManager
from game.level.level_scene import LevelScene
from utils.utils import create_ui_manager_with_theme


class MainMenuScene(AbstractScene):
    def __init__(self):
        super().__init__('main_menu_scene')
        from game.game import Game
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        # self.plant_select_container = PlantSelectContainer()
        self.background_image = pygame.image.load('resources/background/MainMenu.png')


    def update(self, dt: float) -> None:
        # self.plant_select_container.update(dt)
        self.ui_manager.update(dt)

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        screen.blit(self.background_image, Vector2(0,0))
        # self.plant_select_container.draw(screen, bgsurf, special_flags)
        self.ui_manager.draw_ui(screen)

    def process_ui_event(self, event) -> None:
        super().process_ui_event(event)
        # self.plant_select_container.process_event(event)

    def setup_ui(self, *args, **kwargs) -> None:
        start_game_button_rect = Rect(0,0,370,158)
        start_game_button_rect.topright = (-65,60)
        # 主页面开始按钮
        start_game_button = UIButton(
            relative_rect=start_game_button_rect,
            text='',
            manager=self.ui_manager,
            object_id='#start_game_button',
            anchors={
                'right': 'right',
                'top': 'top'
            }
        )
        # 主页面退出游戏按钮
        exit_game_button_rect = Rect(0,0,70,30)
        exit_game_button_rect.bottomright = (-30, -65)
        exit_game_button = UIButton(
            relative_rect=exit_game_button_rect,
            text='退出',
            manager=self.ui_manager,
            object_id='#exit_game_button',
            anchors={
                'right': 'right',
                'bottom': 'bottom'
            }
        )
        # self.plant_select_container.setup()

    def detach_scene(self):
        EventBus().unsubscribe(ButtonClickEvent, self._on_exit_game)
        EventBus().unsubscribe(ButtonClickEvent, self._on_start_game)

    def setup_scene(self, manager: SceneManager) -> None:
        EventBus().subscribe(ButtonClickEvent, self._on_exit_game)
        EventBus().subscribe(ButtonClickEvent, self._on_start_game)

    def _on_exit_game(self, event: ButtonClickEvent):
        if "#exit_game_button" in event.ui_element.object_ids:
            from game.game import Game
            Game.end()

    def _on_start_game(self, event: ButtonClickEvent):
        if "#start_game_button" in event.ui_element.object_ids:
            SceneManager().push_scene(LevelScene('./resources/level/first_day/first_day.tmx', "first_day"))

