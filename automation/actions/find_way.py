import math
import json
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class DangerZone:
    name: str
    zone_type: str  # 'circle' or 'polygon'
    center: Tuple[float, float] = None
    radius: float = None
    points: List[Tuple[float, float]] = None
    threat_level: str  # 'low', 'medium', 'high'

    def get_safety_distance(self, player_level: int) -> float:
        """根据威胁等级和玩家等级计算安全距离"""
        base_distances = {"low": 30, "medium": 50, "high": 80}
        # 玩家等级越高，安全距离可以适当减小
        level_factor = max(0.5, 1.0 - (player_level - 1) * 0.01)
        return base_distances[self.threat_level] * level_factor


@dataclass
class PathNode:
    position: Tuple[float, float]
    g_cost: float = 0  # 从起点到该节点的成本
    h_cost: float = 0  # 到终点的预估成本
    parent: "PathNode" = None

    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost


class SafePathFinder:
    def __init__(self, player_config_path: str, map_config_path: str):
        self.player_config = self._load_player_config(player_config_path)
        self.map_config = self._load_map_config(map_config_path)
        self.current_map = "艾尔文森林"  # 默认地图，需要根据实际情况更新

    def _load_player_config(self, config_path: str) -> Dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_map_config(self, config_path: str) -> Dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_current_danger_zones(self) -> List[DangerZone]:
        """获取当前地图和玩家等级对应的危险区域"""
        map_data = self.map_config["maps"].get(self.current_map)
        if not map_data:
            return []

        danger_zones = []
        player_level = self.player_config["player_level"]

        for level_range, zones in map_data["danger_zones"].items():
            min_level, max_level = map(int, level_range.split("-"))
            if min_level <= player_level <= max_level:
                for zone_data in zones:
                    if zone_data["zone_type"] == "circle":
                        zone = DangerZone(
                            name=zone_data["name"],
                            zone_type="circle",
                            center=tuple(zone_data["center"]),
                            radius=zone_data["radius"],
                            threat_level=zone_data["threat_level"],
                        )
                    else:  # polygon
                        zone = DangerZone(
                            name=zone_data["name"],
                            zone_type="polygon",
                            points=[tuple(point) for point in zone_data["points"]],
                            threat_level=zone_data["threat_level"],
                        )
                    danger_zones.append(zone)

        return danger_zones

    def find_safe_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        grid_size: float = 10.0,
    ) -> Optional[List[Tuple[float, float]]]:
        """寻找避开危险区域的安全路径"""
        danger_zones = self.get_current_danger_zones()

        # 如果起点或终点在危险区域内，直接返回None
        if self._is_position_dangerous(
            start, danger_zones
        ) or self._is_position_dangerous(end, danger_zones):
            print("❌ 起点或终点在危险区域内")
            return None

        # 使用A*算法寻找安全路径
        path = self._a_star_search(start, end, danger_zones, grid_size)

        if path:
            print(f"✅ 找到安全路径，包含 {len(path)} 个路径点")
        else:
            print("❌ 未找到安全路径")

        return path

    def _a_star_search(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        danger_zones: List[DangerZone],
        grid_size: float,
    ) -> Optional[List[Tuple[float, float]]]:
        """A*寻路算法实现"""
        open_set = []
        closed_set = set()

        start_node = PathNode(start)
        start_node.h_cost = self._heuristic(start, end)
        open_set.append(start_node)

        while open_set:
            # 找到f成本最低的节点
            current_node = min(open_set, key=lambda node: node.f_cost)
            open_set.remove(current_node)
            closed_set.add(current_node.position)

            # 如果到达终点
            if self._heuristic(current_node.position, end) < grid_size:
                return self._reconstruct_path(current_node)

            # 探索邻居节点
            for neighbor_pos in self._get_neighbors(current_node.position, grid_size):
                if neighbor_pos in closed_set:
                    continue

                # 检查节点是否安全
                if self._is_position_dangerous(neighbor_pos, danger_zones):
                    closed_set.add(neighbor_pos)
                    continue

                # 计算移动成本
                move_cost = self._calculate_move_cost(
                    current_node.position, neighbor_pos, danger_zones
                )
                g_cost = current_node.g_cost + move_cost

                # 检查是否已经在open_set中
                existing_node = next(
                    (node for node in open_set if node.position == neighbor_pos), None
                )

                if existing_node is None:
                    neighbor_node = PathNode(neighbor_pos)
                    neighbor_node.g_cost = g_cost
                    neighbor_node.h_cost = self._heuristic(neighbor_pos, end)
                    neighbor_node.parent = current_node
                    open_set.append(neighbor_node)
                elif g_cost < existing_node.g_cost:
                    existing_node.g_cost = g_cost
                    existing_node.parent = current_node

        return None

    def _get_neighbors(
        self, position: Tuple[float, float], grid_size: float
    ) -> List[Tuple[float, float]]:
        """获取邻居位置（8方向）"""
        x, y = position
        neighbors = []

        for dx in [-grid_size, 0, grid_size]:
            for dy in [-grid_size, 0, grid_size]:
                if dx == 0 and dy == 0:
                    continue
                neighbors.append((x + dx, y + dy))

        return neighbors

    def _heuristic(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """估算两点之间的距离（曼哈顿距离）"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _calculate_move_cost(
        self,
        from_pos: Tuple[float, float],
        to_pos: Tuple[float, float],
        danger_zones: List[DangerZone],
    ) -> float:
        """计算移动成本，考虑危险区域"""
        base_cost = math.sqrt(
            (from_pos[0] - to_pos[0]) ** 2 + (from_pos[1] - to_pos[1]) ** 2
        )

        # 增加靠近危险区域的惩罚成本
        danger_penalty = 0
        for zone in danger_zones:
            distance_to_zone = self._distance_to_zone(to_pos, zone)
            safety_distance = zone.get_safety_distance(
                self.player_config["player_level"]
            )

            if distance_to_zone < safety_distance:
                # 距离危险区域越近，惩罚越大
                penalty_factor = 1.0 - (distance_to_zone / safety_distance)
                threat_multiplier = {"low": 2, "medium": 5, "high": 10}[
                    zone.threat_level
                ]
                danger_penalty += penalty_factor * threat_multiplier * base_cost

        return base_cost + danger_penalty

    def _distance_to_zone(
        self, position: Tuple[float, float], zone: DangerZone
    ) -> float:
        """计算位置到危险区域的距离"""
        if zone.zone_type == "circle":
            center_distance = math.sqrt(
                (position[0] - zone.center[0]) ** 2
                + (position[1] - zone.center[1]) ** 2
            )
            return max(0, center_distance - zone.radius)
        else:  # polygon
            # 简化处理：计算到多边形最近顶点的距离
            min_distance = float("inf")
            for point in zone.points:
                distance = math.sqrt(
                    (position[0] - point[0]) ** 2 + (position[1] - point[1]) ** 2
                )
                min_distance = min(min_distance, distance)
            return min_distance

    def _is_position_dangerous(
        self, position: Tuple[float, float], danger_zones: List[DangerZone]
    ) -> bool:
        """检查位置是否在危险区域内"""
        for zone in danger_zones:
            if self._is_in_danger_zone(position, zone):
                return True
        return False

    def _is_in_danger_zone(
        self, position: Tuple[float, float], zone: DangerZone
    ) -> bool:
        """检查位置是否在特定危险区域内"""
        if zone.zone_type == "circle":
            distance = math.sqrt(
                (position[0] - zone.center[0]) ** 2
                + (position[1] - zone.center[1]) ** 2
            )
            safety_distance = zone.get_safety_distance(
                self.player_config["player_level"]
            )
            return distance <= (zone.radius + safety_distance)
        else:  # polygon
            # 简化：使用边界框检查
            x_coords = [p[0] for p in zone.points]
            y_coords = [p[1] for p in zone.points]
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)

            # 扩展边界考虑安全距离
            safety_distance = zone.get_safety_distance(
                self.player_config["player_level"]
            )
            return (
                min_x - safety_distance <= position[0] <= max_x + safety_distance
                and min_y - safety_distance <= position[1] <= max_y + safety_distance
            )

    def _reconstruct_path(self, end_node: PathNode) -> List[Tuple[float, float]]:
        """重构路径"""
        path = []
        current = end_node
        while current:
            path.append(current.position)
            current = current.parent
        return path[::-1]  # 反转路径，从起点到终点
