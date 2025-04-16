import pygame.mouse
from pygame import Surface, Vector2
from pygame_gui import UIManager

from base.resource_loader import ResourceLoader


def fit_image_to_size(image_surf: Surface, target_width, target_height):
    """
    将图片保持比例缩放到刚好覆盖指定大小的区域，不修改原图片
    :param image_surf: 需要缩放的图片
    :param target_width: 目标宽
    :param target_height: 目标高
    :return: 缩放后的图片
    """
    img_w, img_h = image_surf.get_size()
    scale_w = target_width / img_w
    scale_h = target_height / img_h
    scale = max(scale_w, scale_h)

    new_size = (int(img_w * scale), int(img_h * scale))
    import pygame
    scaled_image = pygame.transform.smoothscale(image_surf, new_size)

    # 居中裁剪（optional，如果你想跟 CSS 一样只显示屏幕中间）
    x = (scaled_image.get_width() - target_width) // 2
    y = (scaled_image.get_height() - target_height) // 2
    cropped_surface = scaled_image.subsurface(pygame.Rect(x, y, target_width, target_height)).copy()

    return cropped_surface

def create_ui_manager_with_theme(size: tuple[int, int], theme_path: str='resources/ui') -> UIManager:
    manager = UIManager(size, starting_language='zh')
    ResourceLoader().load_theme_to_manager(theme_path, manager)
    return manager

def get_mouse_world_pos(camera_pos: Vector2) -> Vector2:
    """
    获取鼠标世界坐标
    :param camera_pos: 相机的世界坐标
    :return: 鼠标世界坐标位置
    """
    return Vector2(pygame.mouse.get_pos()) + camera_pos