# database/manager.py

import json
import logging
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import text

from .models import CameraMove, EntityData, PlayerMove, UnknownEntity
from .operations import DatabaseOperations

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器，提供高级数据操作功能"""

    def __init__(self):
        self.operations = DatabaseOperations()

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        session = self.operations.get_session()
        try:
            from sqlalchemy import func

            stats = {}

            # 玩家移动统计
            player_count = session.query(func.count(PlayerMove.id)).scalar()
            latest_player_move = (
                session.query(PlayerMove).order_by(PlayerMove.timestamp.desc()).first()
            )

            # 视角移动统计
            camera_count = session.query(func.count(CameraMove.id)).scalar()
            latest_camera_move = (
                session.query(CameraMove).order_by(CameraMove.timestamp.desc()).first()
            )

            # 实体统计
            entity_count = session.query(func.count(EntityData.id)).scalar()
            plant_count = (
                session.query(func.count(EntityData.id))
                .filter(EntityData.entity_type == "plant")
                .scalar()
            )
            ore_count = (
                session.query(func.count(EntityData.id))
                .filter(EntityData.entity_type == "ore")
                .scalar()
            )
            unknown_count = (
                session.query(func.count(EntityData.id))
                .filter(EntityData.is_unknown.is_(True))
                .scalar()
            )

            # 未知实体统计
            unknown_entity_count = session.query(func.count(UnknownEntity.id)).scalar()

            stats.update(
                {
                    "player_moves_total": player_count,
                    "camera_moves_total": camera_count,
                    "entities_total": entity_count,
                    "plants_total": plant_count,
                    "ores_total": ore_count,
                    "unknown_entities_total": unknown_count,
                    "unknown_entity_types": unknown_entity_count,
                    "latest_update": (
                        latest_player_move.timestamp if latest_player_move else None,
                        latest_camera_move.timestamp if latest_camera_move else None,
                    ),
                }
            )

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
        finally:
            session.close()

    def optimize_database(self) -> bool:
        """优化数据库性能"""
        try:
            session = self.operations.get_session()
            # 执行 SQLite 优化命令
            session.execute(text("VACUUM"))
            session.execute(text("ANALYZE"))
            session.commit()
            logger.info("数据库优化完成")
            return True
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()
db_manager = DatabaseManager()
db_manager = DatabaseManager()
