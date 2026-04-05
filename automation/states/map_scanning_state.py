import math
import time
import json
from typing import Any, Dict, List, Optional, Tuple

from automation.utils.adb_operator import adb
from config import settings

from ..core.base_state import BaseState
from ..core.context import GameStatus


class MapScanningState(BaseState):
    """地图扫描状态 - 使用蛇形扫描算法扫描地图"""

    def __init__(self, context):
        super().__init__(context)
        self.scan_complete = False
        self.minerals_found = []
        self.map_scanner = MapScanner()

        # 扫描状态跟踪
        self.scan_started = False
        self.current_vertical_move = 0
        self.current_horizontal_move = 0
        self.direction_right = False
        self.horizontal_moves = 0
        self.vertical_moves = 0

    def enter(self, **kwargs) -> None:
        self.context.set_state(GameStatus.MAP_SCANNING)
        self.scan_complete = False
        self.minerals_found = []
        self.scan_started = False
        self.current_vertical_move = 0
        self.current_horizontal_move = 0
        self.direction_right = False
        self.horizontal_moves = 0
        self.vertical_moves = 0

        print("开始地图扫描...")

        # 从上下文获取目标地图ID，如果没有则使用默认
        target_map_id = kwargs.get("map_id") or getattr(
            self.context, "target_map_id", None
        )
        if target_map_id:
            if not self.map_scanner.set_current_map(target_map_id):
                print(f"无法设置地图 {target_map_id}，使用默认地图")
                self.map_scanner.set_current_map(None)
        else:
            self.map_scanner.set_current_map(None)

    def execute(self) -> Optional[GameStatus]:
        if self.scan_complete:
            # 扫描完成，根据结果决定下一步
            # if self.minerals_found:
            # print(f"扫描完成，找到 {len(self.minerals_found)} 个矿物")
            # 保存扫描结果到上下文
            # self.context.set_state_data("minerals_found", self.minerals_found)
            # return GameStatus.TARGET_SELECTING
            # else:
            # print("当前地图没有找到矿物")
            # return GameStatus.MAP_TRANSITION
            # 扫描完成，返回空闲状态
            print(f"扫描完成，找到 {len(self.minerals_found)} 个矿物")
            # 保存扫描结果到上下文
            self.context.set_state_data("minerals_found", self.minerals_found)
            return GameStatus.IDLE  # 直接返回空闲状态

        # 执行蛇形扫描（分步执行，避免阻塞）
        if not self.scan_started:
            self._initialize_scan()
        else:
            self._perform_snake_scan_step()

        return None

    def _initialize_scan(self):
        """初始化扫描参数"""
        print("初始化扫描参数...")

        # 计算扫描参数
        self.horizontal_moves, self.vertical_moves = (
            self.map_scanner.calculate_scan_parameters()
        )

        # 移动到起始位置
        if self.map_scanner.move_to_start_position():
            time.sleep(self.map_scanner.swipe_wait_time)
            self.scan_started = True
            self.current_vertical_move = 0
            self.current_horizontal_move = 0
            self.direction_right = False  # 从右向左开始扫描

            map_config = self.map_scanner.get_current_map_config()
            print(f"开始扫描地图: {map_config.get('map_name', '未知地图')}")
            print(
                f"扫描范围: {self.horizontal_moves} 横向移动 × {self.vertical_moves} 纵向移动"
            )
        else:
            print("移动到起始位置失败")
            self.scan_complete = True

    def _perform_snake_scan_step(self):
        """执行单步蛇形扫描"""
        if self.current_vertical_move >= self.vertical_moves:
            # 扫描完成
            self.scan_complete = True
            print("蛇形扫描完成!")
            return

        print(f"第 {self.current_vertical_move + 1}/{self.vertical_moves} 行扫描...")

        # 执行当前行的水平扫描
        if self.current_horizontal_move < self.horizontal_moves:
            # 水平移动
            if self.map_scanner.horizontal_swipe(right=self.direction_right):
                self.current_horizontal_move += 1
                time.sleep(self.map_scanner.move_wait_time)

                # 在移动过程中检测矿物
                # self._detect_minerals_during_scan()
            else:
                print(f"横向移动失败 at step {self.current_horizontal_move + 1}")
                self.scan_complete = True
        else:
            # 当前行扫描完成，移动到下一行
            if self.current_vertical_move < self.vertical_moves - 1:
                # 向下移动三次
                for i in range(3):
                    if self.map_scanner.vertical_swipe(up=False):
                        time.sleep(self.map_scanner.move_wait_time)

                        # 在移动过程中检测矿物
                        # self._detect_minerals_during_scan()
                    else:
                        print(f"向下移动失败 at row {self.current_vertical_move + 1}")
                        self.scan_complete = True
                        return

                time.sleep(self.map_scanner.swipe_wait_time)

            # 准备下一行扫描
            self.current_vertical_move += 1
            self.current_horizontal_move = 0
            self.direction_right = not self.direction_right
            print(f"第 {self.current_vertical_move} 行扫描完成")

    # def _detect_minerals_during_scan(self):
    # """在扫描过程中检测矿物"""
    # TODO: 实现矿物检测逻辑
    # 这里可以调用图像识别模块来检测屏幕上的矿物
    # 暂时使用模拟数据

    # 模拟检测逻辑 - 随机生成一些矿物
    # import random

    # if random.random() < 0.1:  # 10%的概率发现矿物
    # mineral_types = ["iron", "copper", "silver", "gold"]
    # mineral_type = random.choice(mineral_types)

    # 基于当前位置生成矿物坐标
    # mineral_x = self.map_scanner.current_x + random.randint(-5, 5)
    # mineral_y = self.map_scanner.current_y + random.randint(-5, 5)
    # distance = random.randint(30, 100)

    # mineral_data = {
    # "type": mineral_type,
    # "position": (mineral_x, mineral_y),
    # "distance": distance,
    # "map_id": self.map_scanner.current_map_id,
    # }

    # 检查是否已经记录过相同位置的矿物
    # if not self._is_mineral_duplicate(mineral_data):
    # self.minerals_found.append(mineral_data)
    # print(f"发现矿物: {mineral_type} 在位置 ({mineral_x}, {mineral_y})")

    #  def _is_mineral_duplicate(self, new_mineral: Dict[str, Any]) -> bool:
    #     """检查是否已经记录过相同位置的矿物"""
    #     for existing_mineral in self.minerals_found:
    #         existing_pos = existing_mineral["position"]
    #         new_pos = new_mineral["position"]

    #         # 如果位置相近（在5个单位内），认为是同一个矿物
    #         distance = math.sqrt(
    #             (existing_pos[0] - new_pos[0]) ** 2
    #             + (existing_pos[1] - new_pos[1]) ** 2
    #         )
    #         if distance < 5 and existing_mineral["type"] == new_mineral["type"]:
    #             return True
    #     return False

    def exit(self) -> None:
        # 保存扫描结果到上下文
        self.context.set_state_data("minerals_found", self.minerals_found)
        self.context.set_state_data(
            "current_position", (self.map_scanner.current_x, self.map_scanner.current_y)
        )
        print("地图扫描状态退出")


# 确保MapScanner类在同一个文件中可用
class MapScanner:
    def __init__(self, config_path: str = "config/map_config.json"):
        self.config_path = config_path
        self.config = self.load_config()

        # 从settings.py读取初始坐标，如果没有则默认为(0,0)
        self.initial_x = getattr(settings, "INITIAL_X", 0)
        self.initial_y = getattr(settings, "INITIAL_Y", 0)

        self.current_x = self.initial_x
        self.current_y = self.initial_y
        self.current_map_id = None

        # 滑动参数 (水平)
        self.horizontal_swipe_start_x = 300
        self.horizontal_swipe_start_y = 360
        self.horizontal_swipe_end_x = 941
        self.horizontal_swipe_end_y = 360
        self.horizontal_swipe_duration = 150
        # 竖直
        self.vertical_swipe_start_x = 500
        self.vertical_swipe_start_y = 520
        self.vertical_swipe_end_x = 500
        self.vertical_swipe_end_y = 200
        self.vertical_swipe_duration = 150

        self.swipe_wait_time = 0.1
        self.move_wait_time = 0.1

        # 坐标变化量 - 固定值
        self.horizontal_move_delta = 10
        self.vertical_move_delta = 5

    def load_config(self) -> Dict[str, Any]:
        """加载地图配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                print("地图配置加载成功")
                return config
        except FileNotFoundError:
            print(f"配置文件 {self.config_path} 未找到")
            return {"maps": {}, "default_map": ""}
        except json.JSONDecodeError:
            print("配置文件格式错误")
            return {"maps": {}, "default_map": ""}

    def get_available_maps(self) -> List[str]:
        """获取可用的地图列表"""
        return list(self.config.get("maps", {}).keys())

    def set_current_map(self, map_id: Optional[str] = None) -> bool:
        """设置当前扫描的地图"""
        if map_id is None:
            # 使用settings中的默认地图
            map_id = settings.SCAN_MAP_ID

        maps = self.config.get("maps", {})
        if map_id not in maps:
            print(f"地图ID '{map_id}' 不存在")
            available_maps = self.get_available_maps()
            print(f"可用的地图: {available_maps}")
            return False

        self.current_map_id = map_id
        map_config = maps[map_id]

        print(f"已切换到地图: {map_config.get('map_name', map_id)}")
        return True

    def get_current_map_config(self) -> Dict[str, Any]:
        """获取当前地图的配置"""
        if self.current_map_id is None:
            if not self.set_current_map(settings.SCAN_MAP_ID):
                return {}

        return self.config.get("maps", {}).get(self.current_map_id, {})

    def move_to_start_position(self) -> bool:
        """移动到地图右上角起始位置"""
        print("正在移动到地图右上角...")
        print(f"初始位置: ({self.initial_x}, {self.initial_y})")

        map_config = self.get_current_map_config()
        map_width = map_config.get("map_width", 500)
        map_height = map_config.get("map_height", 500)

        # 计算需要移动的步数（多加一步确保完全移动到）
        # 向右移动到X最大值：需要移动的距离 = 地图宽度 - 初始X坐标
        horizontal_moves_needed = (
            math.ceil((map_width - self.initial_x) / self.horizontal_move_delta) + 1
        )

        # 向上移动到Y最大值：需要移动的距离 = 地图高度 - 初始Y坐标
        vertical_moves_needed = (
            math.ceil((map_height - self.initial_y) / self.vertical_move_delta) + 1
        )

        print(
            f"需要向右滑动{horizontal_moves_needed}次，向上滑动{vertical_moves_needed}次到达起始位置"
        )
        print(f"目标位置: X={map_width}, Y={map_height}")

        # 向右滑动到最右边
        for i in range(horizontal_moves_needed):
            if not self.horizontal_swipe(right=True):
                return False
            time.sleep(self.move_wait_time)

        # 向上滑动到最上边
        for i in range(vertical_moves_needed):
            if not self.vertical_swipe(up=True):
                return False
            time.sleep(self.move_wait_time)

        self.current_x = map_width
        self.current_y = map_height

        print(f"已移动到起始位置(右上角): ({self.current_x}, {self.current_y})")
        return True

    def horizontal_swipe(self, right: bool = True) -> bool:
        """水平滑动"""
        if right:
            start_x = self.horizontal_swipe_end_x
            start_y = self.horizontal_swipe_end_y
            end_x = self.horizontal_swipe_start_x
            end_y = self.horizontal_swipe_start_y
            self.current_x += self.horizontal_move_delta
            direction = "向右"
        else:
            start_x = self.horizontal_swipe_start_x
            start_y = self.horizontal_swipe_start_y
            end_x = self.horizontal_swipe_end_x
            end_y = self.horizontal_swipe_end_y
            self.current_x -= self.horizontal_move_delta
            direction = "向左"

        success = adb.swipe(
            start_x, start_y, end_x, end_y, self.horizontal_swipe_duration
        )
        if success:
            print(
                f"水平滑动 {direction}, 当前位置: ({self.current_x}, {self.current_y})"
            )
        else:
            print(f"水平滑动 {direction} 失败!")
        return success

    def vertical_swipe(self, up: bool = True) -> bool:
        """垂直滑动"""
        if up:
            start_x = self.vertical_swipe_end_x
            start_y = self.vertical_swipe_end_y
            end_x = self.vertical_swipe_start_x
            end_y = self.vertical_swipe_start_y
            self.current_y += self.vertical_move_delta  # 向上移动Y坐标增加
            direction = "向上"
        else:
            start_x = self.vertical_swipe_start_x
            start_y = self.vertical_swipe_start_y
            end_x = self.vertical_swipe_end_x
            end_y = self.vertical_swipe_end_y
            self.current_y -= self.vertical_move_delta  # 向下移动Y坐标减少
            direction = "向下"

        success = adb.swipe(
            start_x, start_y, end_x, end_y, self.vertical_swipe_duration
        )
        if success:
            print(
                f"垂直滑动 {direction}, 当前位置: ({self.current_x}, {self.current_y})"
            )
        else:
            print(f"垂直滑动 {direction} 失败!")
        return success

    def calculate_scan_parameters(self) -> Tuple[int, int]:
        """计算扫描参数"""
        map_config = self.get_current_map_config()
        map_width = map_config.get("map_width", 1000)
        map_height = map_config.get("map_height", 800)

        # 多加一步确保完全覆盖地图
        horizontal_moves = math.ceil(map_width / self.horizontal_move_delta)
        vertical_moves = math.ceil(map_height / self.vertical_move_delta / 3) + 1

        print(
            f"扫描参数: 横向移动次数={horizontal_moves}, 纵向移动次数={vertical_moves}"
        )
        return horizontal_moves, vertical_moves

    def snake_scan(self, map_id: Optional[str] = None) -> bool:
        """执行蛇形扫描"""
        if map_id is not None and not self.set_current_map(map_id):
            return False
        elif map_id is None and not self.set_current_map(None):
            return False

        map_config = self.get_current_map_config()
        if not map_config:
            print("没有可用的地图配置")
            return False

        print(f"开始扫描地图: {map_config.get('map_name', '未知地图')}")
        print(
            f"地图尺寸: {map_config.get('map_width', 0)}x{map_config.get('map_height', 0)}"
        )
        print(f"初始坐标: ({self.initial_x}, {self.initial_y})")

        horizontal_moves, vertical_moves = self.calculate_scan_parameters()

        if not self.move_to_start_position():
            return False

        time.sleep(self.swipe_wait_time)

        direction_right = False  # 从右向左开始扫描（因为起始位置在右上角）

        for vertical_move in range(vertical_moves):
            print(f"第 {vertical_move + 1}/{vertical_moves} 行扫描开始...")

            for i in range(horizontal_moves):
                if not self.horizontal_swipe(right=direction_right):
                    print(f"横向移动失败 at step {i+1}")
                    return False
                time.sleep(self.move_wait_time)

            if vertical_move < vertical_moves - 1:
                # 向下移动三次，每次移动后等待
                for i in range(3):
                    if not self.vertical_swipe(up=False):
                        print(
                            f"向下移动失败 at row {vertical_move + 1}, 第 {i + 1} 次移动"
                        )
                        return False
                    time.sleep(self.move_wait_time)
                time.sleep(self.swipe_wait_time)

            direction_right = not direction_right
            print(f"第 {vertical_move + 1} 行扫描完成")

        print("蛇形扫描完成!")
        return True

    def start_scan(self, map_id: Optional[str] = None) -> bool:
        """开始扫描流程"""
        return self.snake_scan(map_id)

    def show_available_maps(self):
        """显示所有可用的地图"""
        maps = self.config.get("maps", {})
        if not maps:
            print("没有可用的地图配置")
            return

        print("可用的地图:")
        for map_id, map_config in maps.items():
            map_name = map_config.get("map_name", map_id)
            map_size = (
                f"{map_config.get('map_width', 0)}x{map_config.get('map_height', 0)}"
            )
            print(f"  {map_id}: {map_name} ({map_size})")
