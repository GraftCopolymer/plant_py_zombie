import json
import os
from typing import Union, Type, Optional

import pygame.sprite
import pygame_gui.elements
from pygame import Surface, Vector2, Color

from base.game_event import ButtonClickEvent, EventBus, ClickEvent
from base.scene import AbstractScene, SceneManager
from base.sprite.game_sprite import GameSprite
from game.game import Game
from game.level.level_creator import LevelCreator
from game.level.level_scene import LevelScene
from utils.utils import create_ui_manager_with_theme


class LevelCard(GameSprite):
    """
    关卡卡片，用于显示在关卡选择页面
    """
    card_size = Vector2(140, 90)
    card_image_size = Vector2(112, 48)
    def __init__(self, group: Union[pygame.sprite.Group, list], cover: Surface, level_name: str):
        # 关卡封面
        self.cover = Surface(LevelCard.card_size)
        scaled_cover = pygame.transform.scale(cover, LevelCard.card_image_size)
        # 绘制背景色
        self.cover.fill((23, 43, 33))
        # 绘制封面图
        self.cover.blit(scaled_cover, (LevelCard.card_size[0] / 2 - scaled_cover.width / 2, 5))
        # 绘制文本
        font = pygame.Font('resources/ui/HouseofTerror Regular.otf')
        text_surf = font.render(level_name, antialias=True, color=Color(255,255,255))
        self.cover.blit(text_surf, (LevelCard.card_size[0] / 2 - text_surf.width / 2, LevelCard.card_size[1] - text_surf.height - 5))
        super().__init__(group, self.cover)
        # 关卡名称，将会用该名称创建关卡对象
        self.level_name = level_name

    def update(self, dt: float) -> None:
        pass

    def setup_sprite(self, *args, **kwargs) -> None:
        pass



class LevelSelectScene(AbstractScene):
    """
    关卡选择页面，将列出所有可用关卡
    """
    def __init__(self):
        super().__init__(name='level_select_scene')
        # 背景
        self.background = Surface(Game.screen_size)
        self.background.fill((142, 140, 23))
        # 左上角文字
        font = pygame.Font("resources/ui/HouseofTerror Regular.otf", size=30)
        self.text_surf = font.render("Select level", True, Color(0,0,0))
        # ui manager
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        # 加载关卡卡片
        self.level_cards: list[LevelCard] = []
        self._load_available_levels()
        self._layout_cards()

    def _load_available_levels(self):
        level_dir = 'resources/level'
        try:
            for level in os.listdir(level_dir):
                if not os.path.isdir(os.path.join(level_dir, level)): continue
                level_cover_path = os.path.join(level_dir, level, 'cover.jpg')
                if not os.path.isfile(level_cover_path):
                    raise ValueError(f'请提供关卡 {level} 的封面')
                self.level_cards.append(LevelCard([], pygame.image.load(level_cover_path), level))
        except FileNotFoundError:
            print(f'未找到目录: {level_dir}')
        except Exception as e:
            print(f'未知错误: {e}')

    def _layout_cards(self):
        """
        对卡片进行布局
        """
        index = 0
        y_offset = 10
        x_offset = 0
        card_gap = 10
        left_padding = 70
        top_padding = 100
        while index < len(self.level_cards):
            self.level_cards[index].set_position(Vector2(x_offset + left_padding, y_offset + top_padding))
            x_offset += card_gap + self.level_cards[index].rect.width
            index += 1


    def update(self, dt: float) -> None:
        self.ui_manager.update(dt)

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        # 绘制背景
        screen.blit(self.background, (0,0))
        # 绘制左上角文字
        screen.blit(self.text_surf, (20, 20))
        for card in self.level_cards:
            screen.blit(card.image, card.world_pos)
        self.ui_manager.draw_ui(screen)

    def setup_ui(self) -> None:
        back_button_rect = pygame.Rect(0,0, 100, 50)
        back_button_rect.bottomleft = (20, -20)
        pygame_gui.elements.UIButton(
            relative_rect=back_button_rect,
            text='返回',
            object_id='#back_button',
            manager=self.ui_manager,
            anchors= {
                'left': 'left',
                'bottom': 'bottom'
            }
        )

    def mount(self):
        EventBus().subscribe(ButtonClickEvent, self._on_back_button_clicked)
        EventBus().subscribe(ClickEvent, self._on_mouse_click)

    def unmount(self):
        EventBus().unsubscribe(ButtonClickEvent, self._on_back_button_clicked)
        EventBus().unsubscribe(ClickEvent, self._on_mouse_click)

    def _on_back_button_clicked(self, event: 'ButtonClickEvent'):
        if '#back_button' in event.ui_element.object_ids:
            SceneManager().pop_scene()

    def _on_mouse_click(self, event: 'ClickEvent'):
        # 检测点击到了哪个卡片
        target_card: Optional[LevelCard] = None
        print(f'Mouse pos: {event.mouse_pos}')
        for c in self.level_cards:
            print(f'card rect: {c.rect}')
            if c.rect.collidepoint(event.mouse_pos):
                target_card = c
                break
        if target_card is not None:
            SceneManager().push_scene(LevelCreator.create_level(target_card.level_name))