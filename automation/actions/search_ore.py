import sqlite3
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
import time


@dataclass
class Mineral:
    id: int
    name: str
    mineral_type: str
    tier: int
    position: tuple


class ConfigMineralSelector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.priority_list: List[int] = []  # ID优先级列表
        self.known_minerals: Dict[int, Mineral] = {}
        self.available_minerals: List[Mineral] = []  # 当前可用的矿物

    def load_priority_from_json(self, config_path: str):
        """从JSON配置文件加载优先级"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.priority_list = config.get("mineral_priority", [])
            print(f"📁 从配置文件加载 {len(self.priority_list)} 个矿物的优先级")
            print(
                f"🎯 优先级顺序: {self.priority_list[:10]}{'...' if len(self.priority_list) > 10 else ''}"
            )

        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")

    def load_priority_from_list(self, priority_list: List[int]):
        """直接传入优先级列表"""
        self.priority_list = priority_list
        print(f"🎯 设置 {len(self.priority_list)} 个矿物的优先级")

    def refresh_minerals_from_db(self):
        """从数据库刷新所有矿物数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 查询所有矿物基本信息
            query = """
            SELECT id, name, type, tier, pos_x, pos_y 
            FROM minerals 
            WHERE id IN ({})
            """.format(
                ",".join("?" for _ in self.priority_list)
            )

            cursor.execute(query, self.priority_list)

            self.known_minerals.clear()
            for row in cursor.fetchall():
                mineral_id, name, mineral_type, tier, pos_x, pos_y = row

                mineral = Mineral(
                    id=mineral_id,
                    name=name,
                    mineral_type=mineral_type,
                    tier=tier,
                    position=(pos_x, pos_y),
                )
                self.known_minerals[mineral_id] = mineral

            print(f"📋 从数据库加载 {len(self.known_minerals)} 个目标矿物")
            conn.close()

        except Exception as e:
            print(f"❌ 数据库查询失败: {e}")

    def update_available_minerals(self):
        """更新当前可用的矿物列表（不考虑距离和刷新时间）"""
        self.available_minerals = []

        # 按照配置文件的顺序检查每个矿物是否可用
        for mineral_id in self.priority_list:
            if mineral_id in self.known_minerals:
                mineral = self.known_minerals[mineral_id]
                self.available_minerals.append(mineral)

        print(
            f"🔄 可用矿物更新: {len(self.available_minerals)}/{len(self.known_minerals)} 个可用"
        )

    def get_best_mineral(self) -> Optional[Mineral]:
        """根据配置文件顺序选择最佳矿物"""
        if not self.available_minerals:
            return None

        # 直接返回优先级列表中的第一个可用矿物
        best_mineral = self.available_minerals[0]

        print(
            f"🏆 选择矿物: {best_mineral.name} (ID: {best_mineral.id}, T{best_mineral.tier} {best_mineral.mineral_type})"
        )
        return best_mineral

    def get_next_mineral(self, current_mineral_id: int) -> Optional[Mineral]:
        """获取当前矿物的下一个优先级矿物（用于循环采集）"""
        if not self.available_minerals:
            return None

        try:
            # 找到当前矿物在可用列表中的位置
            current_index = None
            for i, mineral in enumerate(self.available_minerals):
                if mineral.id == current_mineral_id:
                    current_index = i
                    break

            if current_index is None:
                # 如果当前矿物不在列表中，返回第一个
                return self.available_minerals[0]

            # 返回下一个矿物（循环）
            next_index = (current_index + 1) % len(self.available_minerals)
            return self.available_minerals[next_index]

        except Exception as e:
            print(f"❌ 获取下一个矿物失败: {e}")
            return self.available_minerals[0] if self.available_minerals else None

    def mark_mineral_collected(self, mineral_id: int):
        """标记矿物已采集（从可用列表中移除）"""
        self.available_minerals = [
            m for m in self.available_minerals if m.id != mineral_id
        ]
        print(
            f"✅ 标记矿物 {mineral_id} 已采集，剩余 {len(self.available_minerals)} 个可用矿物"
        )

    def get_priority_info(self) -> Dict:
        """获取优先级信息"""
        return {
            "total_priority": len(self.priority_list),
            "total_known": len(self.known_minerals),
            "current_available": len(self.available_minerals),
            "next_5_minerals": [m.id for m in self.available_minerals[:5]],
        }
