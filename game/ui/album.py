import os
from typing import Optional

import pygame
import pygame_gui.elements
from pygame import Surface, Color, Vector2, SRCALPHA

from base.game_event import ButtonClickEvent, EventBus
from base.scene import AbstractScene, SceneManager
from game.game import Game
from game.ui.album_gallery import AlbumGallery
from game.ui.title_content_widget import TitleContentWidget
from utils.utils import create_ui_manager_with_theme


class Album(AbstractScene):
    """
    植物和僵尸图鉴
    """

    def __init__(self):
        super().__init__(name="album")
        self.zombie_album_button_rect: Optional[pygame.Rect] = None
        self.plant_album_button_rect: Optional[pygame.Rect] = None
        # 太阳花图标
        self.sun_flower_image: Surface = pygame.image.load('resources/plant/sun_flower/sun_flower_single.png')
        # 僵尸图标
        self.zombie_image: Surface = pygame.image.load('resources/zombie/normal_zombie/Zombie.gif')
        # "图鉴"文本
        self.album_text_surf: Surface = pygame.Font('resources/ui/STHeiti Light.ttc', 40).render('图鉴', True, Color(255,255,255,255))
        self.ui_manager = create_ui_manager_with_theme(Game.screen_size)
        self.background_color = Color((23, 43, 33))
        self.gallery = AlbumGallery(Vector2(Game.screen_size), self._on_gallery_back_pressed_callback)
        self.gallery.visible = False
        self.plant_gallery_items: list[TitleContentWidget] = []
        self.zombie_gallery_items: list[TitleContentWidget] = []

        # 初始化字体
        self.content_font = pygame.font.Font('resources/ui/STHeiti Light.ttc', 14)
        self.title_font = pygame.font.Font('resources/ui/STHeiti Light.ttc', 30)

        self._load_gallery_items_from_file()

    def _load_gallery_items_from_file(self):
        """
        从文件系统中加载植物和僵尸的图鉴信息,
        intro.png/jpg 作为 TitleContentWidget 的 title，
        intro 文本文件的第一行作为 TitleContentWidget 的 content。
        """
        base_path = 'resources' # 你的资源根目录
        plant_path = os.path.join(base_path, 'plant')
        zombie_path = os.path.join(base_path, 'zombie')

        # 初始化字体，用于渲染名称文本作为 content
        self.name_font = self.content_font

        # --- 加载植物图鉴 ---
        if os.path.exists(plant_path) and os.path.isdir(plant_path):
            for plant_name_dir in os.listdir(plant_path):
                plant_dir_full_path = os.path.join(plant_path, plant_name_dir)
                if os.path.isdir(plant_dir_full_path): # 确保是文件夹
                    intro_file_path = os.path.join(plant_dir_full_path, 'intro')
                    title_image_surface = None # 用于存储标题图片 Surface
                    item_name_text = plant_name_dir.replace('_', ' ').title() # 默认名称，如果文件第一行不存在则用这个
                    item_intro_detail_text = "暂无介绍"


                    # 寻找标题图片文件 (intro.png 或 intro.jpg)
                    if os.path.exists(os.path.join(plant_dir_full_path, 'intro.png')):
                        try:
                            title_image_surface = pygame.image.load(os.path.join(plant_dir_full_path, 'intro.png')).convert_alpha()
                        except pygame.error as e:
                            print(f"Error loading plant title image {plant_name_dir}/intro.png: {e}")
                    elif os.path.exists(os.path.join(plant_dir_full_path, 'intro.jpg')):
                        try:
                            title_image_surface = pygame.image.load(os.path.join(plant_dir_full_path, 'intro.jpg')).convert_alpha()
                        except pygame.error as e:
                            print(f"Error loading plant title image {plant_name_dir}/intro.jpg: {e}")
                    else:
                        print(f"Warning: No intro image (intro.png/jpg) found for plant: {plant_name_dir}. Using placeholder for image.")
                        # 如果没有找到图片，可以创建一个空白 Surface 或者一个带有文本的 Surface 作为占位符
                        # 注意：这里的占位符需要根据 TitleContentWidget 的预期尺寸调整，以免布局问题
                        # 简单起见，这里创建30x30的红色方块作为缺失图片的占位符
                        title_image_surface = Surface((60, 60))

                    # 读取介绍文本，只取第一行作为名称
                    if os.path.exists(intro_file_path):
                        try:
                            with open(intro_file_path, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                if first_line:
                                    item_name_text = first_line # 第一行是名称
                                else:
                                    print(f"Warning: Intro file {intro_file_path} is empty or first line is blank.")
                                second_line = f.readline().strip()
                                if second_line:
                                    item_intro_detail_text = second_line  # 第二行是介绍
                                else:
                                    print(f"Warning: Intro file {intro_file_path} is empty or second line is blank.")

                        except Exception as e:
                            print(f"Error reading plant intro file {intro_file_path}: {e}")
                    else:
                        print(f"Warning: Intro text file not found for plant: {plant_name_dir}")

                    # 渲染名称文本作为 content Surface
                    # 由于这里只渲染名称，我们不需要 render_multiline_text 的复杂换行逻辑
                    # 但为了统一和未来的扩展性，也可以继续使用它，或者直接用 font.render
                    # 这里直接使用 font.render 更符合单行文本的场景
                    content_name_surface = self.name_font.render(item_name_text, True, Color(255,255,255,255))

                    # 创建 TitleContentWidget
                    if title_image_surface is None: # 再次检查以防图片加载失败
                        title_image_surface = Surface((60, 60), SRCALPHA)


                    try:
                        plant_widget = TitleContentWidget(
                            title=title_image_surface, # 图片作为标题
                            size=None,
                            content=content_name_surface, # 名称作为内容,
                            gap=5,
                            extra= {
                                'name': item_name_text,
                                'intro': item_intro_detail_text
                            }
                        )
                        self.plant_gallery_items.append(plant_widget)
                    except Exception as e:
                        print(f"Error creating TitleContentWidget for plant {plant_name_dir}: {e}")
        else:
            print(f"Plant resources path not found or not a directory: {plant_path}")
            print(f"Please ensure '{plant_path}' exists and contains plant folders.")


        # --- 加载僵尸图鉴 (与植物类似) ---
        if os.path.exists(zombie_path) and os.path.isdir(zombie_path):
            for zombie_name_dir in os.listdir(zombie_path):
                zombie_dir_full_path = os.path.join(zombie_path, zombie_name_dir)
                if os.path.isdir(zombie_dir_full_path):
                    intro_file_path = os.path.join(zombie_dir_full_path, 'intro')
                    title_image_surface = None
                    item_name_text = zombie_name_dir.replace('_', ' ').title()
                    item_intro_detail_text = "暂无介绍"

                    if os.path.exists(os.path.join(zombie_dir_full_path, 'intro.png')):
                        try:
                            title_image_surface = pygame.image.load(os.path.join(zombie_dir_full_path, 'intro.png')).convert_alpha()
                        except pygame.error as e:
                            print(f"Error loading zombie title image {zombie_name_dir}/intro.png: {e}")
                    elif os.path.exists(os.path.join(zombie_dir_full_path, 'intro.jpg')):
                        try:
                            title_image_surface = pygame.image.load(os.path.join(zombie_dir_full_path, 'intro.jpg')).convert_alpha()
                        except pygame.error as e:
                            print(f"Error loading zombie title image {zombie_name_dir}/intro.jpg: {e}")
                    else:
                        print(f"Warning: No title image (intro.png/jpg) found for zombie: {zombie_name_dir}. Using placeholder for image.")
                        title_image_surface = Surface((60, 60), pygame.SRCALPHA)


                    if os.path.exists(intro_file_path):
                        try:
                            first_line = ""
                            with open(intro_file_path, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                if first_line:
                                    item_name_text = first_line
                                else:
                                    print(f"Warning: Intro file {intro_file_path} is empty or first line is blank.")
                                second_line = f.readline().strip()
                                if second_line:
                                    item_intro_detail_text = second_line  # 第二行是介绍
                                else:
                                    print(f"Warning: Intro file {intro_file_path} is empty or second line is blank.")
                        except Exception as e:
                            print(f"Error reading zombie intro file {intro_file_path}: {e}")
                    else:
                        print(f"Warning: Intro text file not found for zombie: {zombie_name_dir}")

                    content_name_surface = self.name_font.render(item_name_text, True, Color(255,255,255,255))

                    if title_image_surface is None:
                        title_image_surface = Surface((60, 60), pygame.SRCALPHA)

                    try:
                        zombie_widget = TitleContentWidget(
                            title=title_image_surface,
                            size=None,
                            content=content_name_surface,
                            gap=5,
                            extra={
                                'name': item_name_text,
                                'intro': item_intro_detail_text
                            }
                        )
                        self.zombie_gallery_items.append(zombie_widget)
                    except Exception as e:
                        print(f"Error creating TitleContentWidget for zombie {zombie_name_dir}: {e}")
        else:
            print(f"Zombie resources path not found or not a directory: {zombie_path}")
            print(f"Please ensure '{zombie_path}' exists and contains zombie folders.")

    def process_ui_event(self, event) -> None:
        super().process_ui_event(event)
        self.gallery.process_event(event)

    def update(self, dt: float) -> None:
        self.gallery.update(dt)
        self.ui_manager.update(dt)

    def draw(self, screen: Surface, bgsurf=None, special_flags=0) -> None:
        screen.fill(self.background_color) # 深绿色
        screen.blit(self.album_text_surf, (Game.screen_size[0] / 2 - self.album_text_surf.width / 2, 40))
        screen.blit(self.sun_flower_image, (
            (self.plant_album_button_rect.x + self.plant_album_button_rect.width / 2) - self.sun_flower_image.width / 2,
            self.plant_album_button_rect.y - self.sun_flower_image.height)
        ) # 太阳花图标
        screen.blit(self.zombie_image, (
            (self.zombie_album_button_rect.x + self.zombie_album_button_rect.width / 2) - self.zombie_image.width / 2,
            self.zombie_album_button_rect.y - self.zombie_image.height)
        ) # 僵尸图标
        self.ui_manager.draw_ui(screen)
        self.gallery.draw(screen)

    def setup_ui(self, *args, **kwargs) -> None:
        super().setup_ui()
        # 植物图鉴按钮和僵尸图鉴按钮各自在屏幕两等份的区域中间
        half_of_screen_width = Game.screen_size[0] / 2
        screen_height = Game.screen_size[1]
        button_width = 100
        button_height = 50
        # 植物图鉴按钮
        self.plant_album_button_rect = pygame.Rect(0, 0, button_width, button_height)
        self.plant_album_button_rect.topleft = (
        half_of_screen_width / 2 - button_width / 2, screen_height / 2 - button_height / 2)
        pygame_gui.elements.UIButton(
            manager=self.ui_manager,
            relative_rect=self.plant_album_button_rect,
            text='植物图鉴',
            anchors={
                'left': 'left',
                'top': 'top'
            },
            object_id='#plant_album_button'
        )
        # 僵尸图鉴按钮
        self.zombie_album_button_rect = pygame.Rect(0, 0, button_width, button_height)
        self.zombie_album_button_rect.topleft = (
        half_of_screen_width * 3 / 2 - button_width / 2, screen_height / 2 - button_height / 2)
        pygame_gui.elements.UIButton(
            manager=self.ui_manager,
            relative_rect=self.zombie_album_button_rect,
            text='僵尸图鉴',
            anchors={
                'left': 'left',
                'top': 'top'
            },
            object_id='#zombie_album_button'
        )
        album_back_button_rect = pygame.Rect(0, 0, 100, 50)
        album_back_button_rect.topleft = (20, 20)
        pygame_gui.elements.UIButton(
            relative_rect=album_back_button_rect,
            manager=self.ui_manager,
            text='返回',
            anchors={
                'left': 'left',
                'top': 'top'
            },
            object_id='#album_back_button'
        )
        self.gallery.setup()

    def mount(self):
        EventBus().subscribe(ButtonClickEvent, self._on_button_clicked)

    def unmount(self):
        EventBus().unsubscribe(ButtonClickEvent, self._on_button_clicked)
        self.gallery.unmount()
        super().unmount()

    def _on_button_clicked(self, event: 'ButtonClickEvent'):
        ids = event.ui_element.object_ids
        if '#plant_album_button' in ids:
            # 显示植物图鉴列表
            self.gallery.set_content(self.plant_gallery_items)
            self.gallery.visible = True
        elif '#zombie_album_button' in ids:
            # 显示僵尸图鉴列表
            self.gallery.set_content(self.zombie_gallery_items)
            self.gallery.visible = True
            pass
        elif '#album_back_button' in ids and not self.gallery.visible:
            SceneManager().pop_scene()

    def _on_gallery_back_pressed_callback(self) -> None:
        # 当按下图鉴列出控件的返回按钮时，隐藏之
        self.gallery.visible = False

