import pygame
import pygame_gui.elements
from pygame import Surface, Vector2, Color

from base.game_event import ButtonClickEvent, EventBus
from base.scene import AbstractScene, SceneManager
from base.sprite.static_sprite import StaticSprite
from game.game import Game
from utils.utils import create_ui_manager_with_theme


class IntroPage(AbstractScene):
    """
    显示植物或僵尸的详细介绍
    """
    def __init__(self, title: Surface, content: Surface):
        super().__init__(name="intro_page")
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        self.top_padding = 100
        self.gap = 5
        self.background_color = Color(128, 104, 0)
        self.title = StaticSprite([], title, Vector2(0,0))
        self.content = StaticSprite([], content, Vector2(0,0))
        # 计算title和content的显示位置
        self.layout()

    def mount(self):
        EventBus().subscribe(ButtonClickEvent, self._on_button_clicked)

    def unmount(self):
        EventBus().unsubscribe(ButtonClickEvent, self._on_button_clicked)

    def layout(self):
        # 均显示在水平居中位置
        # title距离屏幕顶端self.top_padding
        # content距离title为self.gap
        # content在title正下方
        rect = pygame.Rect(0,0,Game.screen_size[0], Game.screen_size[1])
        self.title.set_position(Vector2(rect.width / 2 - self.title.rect.width / 2, self.top_padding))
        self.content.set_position(Vector2(rect.width / 2 - self.content.rect.width / 2, self.title.world_pos.y + self.title.rect.height + self.gap))

    def update(self, dt: float) -> None:
        self.ui_manager.update(dt)

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        screen.fill(self.background_color)
        screen.blit(self.title.image, self.title.world_pos)
        screen.blit(self.content.image, self.content.world_pos)
        self.ui_manager.draw_ui(screen)

    def setup_ui(self, *args, **kwargs) -> None:
        # 返回按钮
        intro_page_back_button_rect = pygame.Rect(0,0,100,50)
        intro_page_back_button_rect.topleft = (20, 20)
        pygame_gui.elements.UIButton(
            relative_rect=intro_page_back_button_rect,
            manager=self.ui_manager,
            text='返回',
            anchors={
                'left': 'left',
                'top': 'top'
            },
            object_id='#intro_page_back_button'
        )

    def _on_button_clicked(self, event: 'ButtonClickEvent'):
        if '#intro_page_back_button' in event.ui_element.object_ids:
            # 关闭当前场景
            SceneManager().pop_scene()