import pygame.mouse
from pygame import Surface, Vector2, Color
from pygame_gui import UIManager

from base.resource_loader import ResourceLoader
from base.sprite.game_sprite import GameSprite


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

def transform_coor_sys(coor: Vector2, origin_pos: Vector2) -> Vector2:
    """
    将指定坐标位置变化到指定原点所在坐标系的坐标
    :return: 变换后的坐标
    """
    return Vector2(coor.x - origin_pos.x, coor.y - origin_pos.y)

def collide(sp1: GameSprite, sp2: GameSprite):
    """
    对两个GameSprite进行碰撞检测
    若传入的任何一个对象没有矩形属性则返回False
    """
    if not sp2.rect or not sp1.rect: return False
    return pygame.sprite.collide_rect(sp1, sp2)

def render_multiline_text(text: str, font: pygame.font.Font, color: Color, max_width: int) -> Surface:
    """
    渲染多行文本到一个 Surface，支持中文。
    自动根据 max_width 进行换行，尝试保持单词完整（如果存在）。
    对于中文，按字符或标点进行更细粒度的控制。
    :param text: 要渲染的文本。
    :param font: 字体对象。
    :param color: 文本颜色。
    :param max_width: 文本行的最大宽度。
    :return: 包含渲染文本的 Surface。
    """
    lines = []
    # 使用更复杂的策略来处理中英文混合和标点
    # 可以使用正则表达式或者更简单的逐字/逐词策略
    # 这里采用逐字（或逐词）的简单策略，并处理英文单词

    words_or_chars = []
    current_word = ""
    for char in text:
        if 'a' <= char.lower() <= 'z' or char.isdigit():  # 识别英文单词和数字
            current_word += char
        else:  # 非英文/数字字符（包括中文、标点、空格等）
            if current_word:  # 如果有累积的英文单词，先添加
                words_or_chars.append(current_word)
                current_word = ""
            words_or_chars.append(char)  # 添加当前非英文/数字字符
    if current_word:  # 添加末尾可能存在的英文单词
        words_or_chars.append(current_word)

    current_line_parts = []
    current_line_width = 0
    line_height = font.get_linesize()  # 获取字体推荐的行高

    for part in words_or_chars:
        part_width, _ = font.size(part)

        # 如果当前行是空的，直接添加当前部分
        if not current_line_parts:
            current_line_parts.append(part)
            current_line_width = part_width
        else:
            # 尝试添加当前部分，如果超过最大宽度则开始新行
            # 考虑到英文单词之间通常有空格，中文没有
            test_width = current_line_width
            if part.isspace() and current_line_parts and not current_line_parts[-1].isspace():
                test_width += font.size(' ')[0]  # 英文单词间加空格
            test_width += part_width

            if test_width <= max_width:
                current_line_parts.append(part)
                current_line_width = test_width
            else:
                # 如果添加后会超宽，则将当前行添加到 lines，并开始新行
                lines.append("".join(current_line_parts).strip())  # .strip() 移除行尾空格
                current_line_parts = [part]
                current_line_width = part_width

    # 添加最后一行
    if current_line_parts:
        lines.append("".join(current_line_parts).strip())

    if not lines:  # 处理空文本的情况
        return Surface((1, 1), pygame.SRCALPHA)  # 返回一个最小的透明 surface

    # 计算总高度和最大行宽
    total_height = len(lines) * line_height  # 简单地用行数乘以行高
    max_line_width = 0
    for line in lines:
        max_line_width = max(max_line_width, font.size(line)[0])

    # 创建一个足够大的 Surface 来容纳所有文本
    text_surface = Surface((max_line_width, total_height), pygame.SRCALPHA)
    y_offset = 0
    for line in lines:
        line_surface = font.render(line, True, color)
        # 将每行文本居中绘制
        x_offset = (max_line_width - line_surface.get_width()) / 2
        text_surface.blit(line_surface, (x_offset, y_offset))
        y_offset += line_height  # 使用固定的行高
    return text_surface