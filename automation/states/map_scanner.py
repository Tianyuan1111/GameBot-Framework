import json
import math
import time
from re import S
from typing import Any, Dict, List, Optional, Tuple

from automation.utils.adb_operator import adb
from config import settings


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
        horizontal_moves = math.ceil(map_width / self.horizontal_move_delta) + 1
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
