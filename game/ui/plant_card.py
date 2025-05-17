from typing import Union, TypeVar, Type

import pygame.transform
from pygame import Surface, Vector2
from pygame.sprite import Group

from base.sprite.game_sprite import GameSprite
from game.character.plant import AbstractPlant

PlantT = TypeVar("PlantT", bound=AbstractPlant)

class PlantCard(GameSprite):
    disable_mask_color = (70,70,70,0)
    cold_mask_color = (60,60,60,0)
    def __init__(self, group: Union[Group, list], plant_cls: Type[PlantT], plant_name: str, image: Surface, position: Vector2 = Vector2(0, 0)):
        super().__init__(group, image, position)
        self.scale = 0.75
        self.image = image
        # 储存一份原始图片
        self.image = pygame.transform.scale(self.image, (self.image.width * self.scale, self.image.height * self.scale))
        self._origin_image = self.image.copy()
        self.rect = self.image.get_rect()
        self.plant_cls: Type[PlantT] = plant_cls
        self.plant_name = plant_name
        self.rect_offset = Vector2(0,0)

        # 是否禁用
        self.disabled = False
        # 是否处于冷却状态
        self.cold_down = False
        # 冷却计时器
        self.cold_down_timer = 0
        # 禁用状态时显示的遮罩
        self.disabled_mask = Surface(self.rect.size)
        self.disabled_mask.fill(PlantCard.disable_mask_color)
        # 冷却状态时显示的遮罩
        self.cold_down_mask = Surface(self.rect.size)
        self.cold_down_mask.fill(PlantCard.cold_mask_color)

    def update(self, dt: float) -> None:
        self.image = self._origin_image.copy()
        if self.disabled:
            self.image.blit(self.disabled_mask, (0,0), special_flags=pygame.BLEND_RGB_SUB)
        if self.cold_down:
            self.update_cold_down_mask(dt)
            self.image.blit(self.cold_down_mask, (0,0), special_flags=pygame.BLEND_RGB_SUB)
            self.cold_down_timer -= dt
            if self.cold_down_timer <= 0:
                self.cold_down_end()

    def update_cold_down_mask(self, dt: float):
        """
        更新冷却遮罩
        """
        card_size = list(self.rect.size)
        card_size[1] = self.rect.size[1] * (self.cold_down_timer / self.plant_cls.plant_cold_down)
        self.cold_down_mask = Surface(card_size)
        self.cold_down_mask.fill(PlantCard.cold_mask_color)

    def draw(self, surface: Surface, camera_pos: Vector2) -> None:
        """
        本类的绘制由外部完成
        """
        pass

    def setup_sprite(self, *args, **kwargs) -> None:
        super().setup_sprite()
        pass

    def create_plant_instance(self, *args, **kwargs) -> AbstractPlant:
        return self.plant_cls(*args, **kwargs)

    def disable(self):
        self.disabled = True

    def enable(self):
        self.disabled = False

    def cold_down_start(self):
        """
        开始冷却状态
        """
        self.cold_down = True
        self.cold_down_timer = self.plant_cls.plant_cold_down
        # 发布冷却开始事件
        from base.game_event import EventBus, PlantCardStartColdDown
        EventBus().publish(PlantCardStartColdDown(self))

    def cold_down_end(self):
        """
        结束冷却状态
        """
        self.cold_down = False
        self.cold_down_timer = 0
        # 发布冷却结束事件
        from base.game_event import EventBus, PlantCardEndColdDown
        EventBus().publish(PlantCardEndColdDown(self))

    def __copy__(self):
        cls = self.__class__
        res = cls.__new__(cls)

        # 基类字段（GameSprite）
        res.group = self.group
        pygame.sprite.Sprite.__init__(res, res.group)

        res.world_pos = self.world_pos.copy()
        res.direction = self.direction.copy()
        res.speed = self.speed
        res.z = self.z

        res._origin_image = self._origin_image.copy()
        res.image = self.image.copy()
        res.rect = self.rect.copy() if self.rect else None
        res.image_offset = self.image_offset.copy()
        res.rect_offset = self.rect_offset.copy()
        res._old_rect_offset = self._old_rect_offset.copy()
        res.display = self.display

        # PlantCard 特有字段
        res.scale = self.scale
        res.plant_cls = self.plant_cls
        res.plant_name = self.plant_name
        res.disabled = self.disabled
        res.cold_down = self.cold_down
        res.cold_down_timer = self.cold_down_timer

        # 遮罩 Surface（拷贝大小与填充值）
        res.disabled_mask = Surface(self.rect.size, pygame.SRCALPHA)
        res.disabled_mask.fill(PlantCard.disable_mask_color)

        res.cold_down_mask = Surface(self.rect.size, pygame.SRCALPHA)
        res.cold_down_mask.fill(PlantCard.cold_mask_color)

        return res
