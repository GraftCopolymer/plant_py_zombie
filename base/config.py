def gen_layers(layer_names: list[str]) -> dict[str, int]:
    """
    生成图层
    :param layer_names: 图层列表
    :return: 图层名称 -- 图层优先级 字典
    """
    res = {}
    layer = 0
    for name in layer_names:
        res[name] = layer
        layer += 1
    return  res

# 图层，后面图层会显示在前面图层之上
LAYERS = gen_layers([
    "background",
    "plant0",
    "plant1",
    "plant2",
    "plant3",
    "zombie0",
    "zombie1",
    "zombie2",
    "zombie3",
    "zombie4",
    "zombie5",
    "zombie6",
    "zombie7",
    "zombie8",
    "bullet",
    "main",
    'highlight'
])

PLANTS_DIR = {
    "pea_shooter": "./resources/plant/pea_shooter"
}