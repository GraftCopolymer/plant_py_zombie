# plant_py_zombie
## 添加僵尸（Zombie）

在`resources/zombie/`目录下新建一个文件夹，命名为要添加的僵尸名，这里以普通僵尸为例：

新建`resources/zombie/normal_zombie`目录，在该目录中创建文件`normal_zombie.json`注意，json文件名一定要与目录名一致，否则不会被扫描到。

接下来，在`normal_zombie.json`编写僵尸的配置，格式如下：

```json
{
  "id": "normal_zombie", // 僵尸的配置id，请保证全局唯一，否则会被后加载的同名id覆盖
  "animations": { // 僵尸动画列表
    "idle": [ // 不同状态下僵尸的动画，由于相同的僵尸的同样状态也可能有多种动画，所以此处是一个列表，僵尸在生成时将会从中随机选择动画
      {
        "type": "gif", // 动画类型，支持 gif 和 multi_image 两种
        "frames": "./1.gif", // 动画资源路径，该路径是相对于当前json文件的路径
      },
      {
        "type": "multi_image",
        "frames": ["frame1.png", "frame2.png"] // 如果是 multi_image，请传入一个图片列表
        "play_mode": "loop", // 动画播放模式，可选 loop, once, reverse_loop，行为顾名思义，不传默认为 loop
        "interval": 100, // 僵尸动画每帧的时间间隔，越小动画播放速度越快，不传默认150，单位ms
        "init_frame": 1, // 默认起始帧索引（从0开始），不传默认为0
        "play_speed_scale": 2 // 动画播放速度因子，越大播放速度越快，不传默认为1
      },
      {
        "type": "gif",
        "frames": "./dying.gif" 
        "play_mode": "once", // 死亡动画写 once，播放完毕后将会执行渐隐动画并删除该僵尸
      }
    ] 
  },
  "health": { // 僵尸的生命值，传入float最终会被转化为int, 需传入最大和最小生命值，创建僵尸对象时将从该范围内随机一个数字
    "min": 95,
    "max": 100
  },
  "speed": 20, // 僵尸的移动速度，若不传入则默认为0
}
```

游戏启动前会自动扫描`resources/zombie/`文件夹下的所有僵尸配置并进行加载，要创建一个僵尸实例，请实例化`ConfigZombie`类并传入一个`ZombieConfig`，`ZombieConfig`可通过`ConfigManager`获取：

```python
scene_manager = SceneManager() # 场景管理器实例
test_level = LevelScene(pygame.image.load('./resources/scene/first_day/map0.jpg'), "first_day", scene_manager) # 创建一个场景并指定由管理器管理
test_config_zombie = ConfigZombie(ConfigManager().get_zombie_config('normal_zombie'), test_level) # 将僵尸加入一个指定的场景
test_config_zombie.set_position(Position(700, 300))
test_config_zombie.idle() # 设定僵尸状态
```

然后在游戏循环中调用

```python
scene_manager.update(delta)
scene_manager.draw(screen)
```

对于逻辑简单的僵尸，编写配置文件即可，对于逻辑较为复杂的僵尸，需继承`GenericZombie`或`AbstractZombie`实现
