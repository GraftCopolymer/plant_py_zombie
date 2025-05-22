from typing import TYPE_CHECKING

import pygame.image
import pygame_gui.elements
from pygame import Vector2

from base.game_event import ButtonClickEvent, EventBus
from base.scene import SceneManager
from game.ui.ui_widget import UIWidget

if TYPE_CHECKING:
    from game.level.level_scene import LevelScene


class ResultDialog(UIWidget):
    """
    展示关卡结果的对话框
    """
    def __init__(self, level: 'LevelScene'):
        self.win_background = pygame.image.load('resources/level/game_win_dialog_background.png').convert_alpha()
        self.fail_background = pygame.image.load('resources/level/game_fail_dialog_background.png').convert_alpha()
        # 对对话框背景进行缩小，防止显示过大
        self.win_background = pygame.transform.scale(self.win_background, (self.win_background.width * 0.5, self.win_background.height*0.5))
        self.fail_background = pygame.transform.scale(self.fail_background, (self.fail_background.width * 0.5, self.fail_background.height * 0.5))
        super().__init__('#result_dialog', self.win_background)
        self.level = level
        # 记录上一次level的屏蔽状态
        self.last_level_modal_state: bool = False
        # 初始不可见
        self.visible = False
        # 显示在屏幕正中央
        from game.game import Game
        self.screen_pos = Vector2(Game.screen_size[0] / 2 - self.rect.width / 2, Game.screen_size[1] / 2 - self.rect.height / 2)

    def setup(self) -> None:
        # 注意，此处不调用super.setup，因为不需要自动执行mount进行事件绑定
        # 确定按钮
        confirm_button_rect = pygame.Rect(0,0,100,50)
        confirm_button_rect.bottomleft = (self.size.x / 2 - confirm_button_rect.width / 2, -20)
        pygame_gui.elements.UIButton(
            relative_rect=confirm_button_rect,
            text='确定',
            object_id='#result_confirm_button',
            manager=self.ui_manager,
            container=self.panel,
            anchors= {
                'left': 'left',
                'bottom': 'bottom'
            }
        )

    def mount(self) -> None:
        EventBus().subscribe(ButtonClickEvent, self._on_confirm)

    def unmount(self) -> None:
        EventBus().unsubscribe(ButtonClickEvent, self._on_confirm)

    def layout(self) -> None:
        pass

    def show(self, state: str, modal=True):
        """
        显示对话框
        :param state: 'win' 或者 'fail'
        :param modal: 是否屏蔽level下的所有事件
        """
        if state == 'win':
            self.background = self.win_background
        elif state == 'fail':
            self.background = self.fail_background
        else:
            raise ValueError('只能是win或fail!')
        self.visible = True
        # 订阅事件
        self.mount()
        self.last_level_modal_state = False
        if modal:
            # 屏蔽level事件
            self.level.unmount()
            self.last_level_modal_state = True

    def hide(self):
        self.visible = False
        # 取消事件订阅
        self.unmount()
        if self.last_level_modal_state:
            # 恢复level事件
            self.level.mount()

    def _on_confirm(self, event: 'ButtonClickEvent'):
        if '#result_confirm_button' in event.ui_element.object_ids:
            # 退出当前场景
            SceneManager().pop_scene()
