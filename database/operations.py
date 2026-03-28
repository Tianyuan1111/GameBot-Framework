# database/operations.py

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import db_config
from .models import Base, CameraMove, EntityData, PlayerMove, SystemLog, UnknownEntity

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """数据库操作类"""

    def __init__(self):
        self.db_config = db_config
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """确保数据表存在"""
        try:
            Base.metadata.create_all(bind=self.db_config.engine)
            logger.info("数据库表初始化完成")
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            raise

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.db_config.get_session()

    def insert_player_move(
        self,
        position_x: float,
        position_y: float,
        velocity_x: Optional[float] = None,
        velocity_y: Optional[float] = None,
        packet_source: Optional[str] = None,
    ) -> bool:
        """插入玩家移动数据"""
        session = self.get_session()
        try:
            player_move = PlayerMove(
                position_x=position_x,
                position_y=position_y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                packet_source=packet_source,
            )
            session.add(player_move)
            session.commit()
            logger.debug(f"玩家移动数据插入成功: ({position_x:.2f}, {position_y:.2f})")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"插入玩家移动数据失败: {e}")
            return False
        finally:
            session.close()

    def insert_camera_move(
        self,
        angle_x: float,
        angle_y: float,
        delta_x: Optional[float] = None,
        delta_y: Optional[float] = None,
        packet_source: Optional[str] = None,
    ) -> bool:
        """插入视角移动数据"""
        session = self.get_session()
        try:
            camera_move = CameraMove(
                angle_x=angle_x,
                angle_y=angle_y,
                delta_x=delta_x,
                delta_y=delta_y,
                packet_source=packet_source,
            )
            session.add(camera_move)
            session.commit()
            logger.debug(
                f"视角移动数据插入成功: X角度={angle_x:.4f}, Y角度={angle_y:.4f}"
            )
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"插入视角移动数据失败: {e}")
            return False
        finally:
            session.close()

    def insert_entity_data(self, entity_data: Dict[str, Any]) -> bool:
        """插入实体数据"""
        session = self.get_session()
        try:

            # 检查是否已存在相同坐标和类型的实体
            existing_entity = (
                session.query(EntityData)
                .filter(
                    EntityData.position_x == entity_data["position_x"],
                    EntityData.position_y == entity_data["position_y"],
                    EntityData.entity_type == entity_data["entity_type"],
                )
                .first()
            )

            if existing_entity:
                logger.debug(
                    f"实体数据已存在，跳过插入: {entity_data['entity_name']} "
                    f"({entity_data['position_x']:.2f}, {entity_data['position_y']:.2f}) "
                    f"类型: {entity_data['entity_type']}"
                )
                return True  # 或者返回False，根据你的业务需求

            entity = EntityData(
                entity_id=entity_data["entity_id"],
                entity_type=entity_data["entity_type"],
                entity_name=entity_data["entity_name"],
                category=entity_data.get("category"),
                growth_stage=entity_data.get("growth_stage"),
                maturity_level=entity_data.get("maturity_level", 0),
                is_mature=entity_data.get("is_mature", False),
                position_x=entity_data["position_x"],
                position_y=entity_data["position_y"],
                entity_index=entity_data.get("entity_index"),
                is_unknown=entity_data.get("is_unknown", False),
                raw_data=entity_data.get("raw_data"),
            )
            session.add(entity)
            session.commit()
            logger.debug(
                f"实体数据插入成功: {entity_data['entity_name']} "
                f"({entity_data['position_x']:.2f}, {entity_data['position_y']:.2f})"
                f"阶数:{entity_data.get('maturity_level', 0)}"
            )
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"插入实体数据失败: {e}")
            return False
        finally:
            session.close()

    def record_unknown_entity(
        self,
        entity_id: int,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        raw_hex_data: Optional[str] = None,
    ) -> bool:
        """记录未知实体 - 直接创建新记录"""
        session = self.get_session()
        try:

            # 直接创建新记录，不检查是否已存在
            unknown_entity = UnknownEntity(
                entity_id=entity_id,
                position_x=position_x,
                position_y=position_y,
                raw_hex_data=raw_hex_data,
            )
            session.add(unknown_entity)
            session.commit()
            logger.info(f"未知实体记录已创建: {entity_id}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"记录未知实体失败: {e}")
            return False
        finally:
            session.close()

    def log_system_event(
        self, level: str, message: str, module: Optional[str] = None
    ) -> bool:
        """记录系统事件"""
        session = self.get_session()
        try:
            log_entry = SystemLog(level=level, message=message, module=module)
            session.add(log_entry)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"记录系统日志失败: {e}")
            return False
        finally:
            session.close()

    # 查询方法
    def get_recent_player_moves(self, limit: int = 100) -> List[PlayerMove]:
        """获取最近的玩家移动数据"""
        session = self.get_session()
        try:
            moves = (
                session.query(PlayerMove)
                .order_by(PlayerMove.timestamp.desc())
                .limit(limit)
                .all()
            )
            return moves
        except SQLAlchemyError as e:
            logger.error(f"查询玩家移动数据失败: {e}")
            return []
        finally:
            session.close()

    def get_player_moves(self, limit: int = 1000) -> List[PlayerMove]:
        """获取玩家移动数据"""
        session = self.get_session()
        try:
            moves = (
                session.query(PlayerMove)
                .order_by(PlayerMove.timestamp.desc())
                .limit(limit)
                .all()
            )
            return moves
        except SQLAlchemyError as e:
            logger.error(f"查询玩家移动数据失败: {e}")
            return []
        finally:
            session.close()

    def get_recent_camera_moves(self, limit: int = 100) -> List[CameraMove]:
        """获取最近的视角移动数据"""
        session = self.get_session()
        try:
            camera_moves = (
                session.query(CameraMove)
                .order_by(CameraMove.timestamp.desc())
                .limit(limit)
                .all()
            )
            return camera_moves
        except SQLAlchemyError as e:
            logger.error(f"获取视角移动数据失败: {e}")
            return []
        finally:
            session.close()

    def get_camera_moves(self, limit: int = 1000) -> List[CameraMove]:
        """获取视角移动数据"""
        session = self.get_session()
        try:
            camera_moves = (
                session.query(CameraMove)
                .order_by(CameraMove.timestamp.desc())
                .limit(limit)
                .all()
            )
            return camera_moves
        except SQLAlchemyError as e:
            logger.error(f"获取视角移动数据失败: {e}")
            return []
        finally:
            session.close()

    def get_entities_by_type(self, entity_type: str) -> List[EntityData]:
        """根据类型获取实体数据"""
        session = self.get_session()
        try:
            entities = (
                session.query(EntityData)
                .filter(EntityData.entity_type == entity_type)
                .order_by(EntityData.timestamp.desc())
                .all()
            )
            return entities
        except SQLAlchemyError as e:
            logger.error(f"查询实体数据失败: {e}")
            return []
        finally:
            session.close()

    def get_all_entities(self) -> List[EntityData]:
        """
        获取所有实体数据

        Returns:
            List[EntityData]: 实体数据列表
        """
        session = self.get_session()
        try:
            return session.query(EntityData).all()
        except SQLAlchemyError as e:
            logger.error(f"查询所有实体数据失败: {e}")
            return []
        finally:
            session.close()

    def get_all_entities_dict(self) -> List[dict]:
        """
        获取所有实体数据并转换为字典

        Returns:
            List[dict]: 实体数据字典列表
        """
        session = self.get_session()
        try:
            entities = session.query(EntityData).all()
            return [entity.to_dict() for entity in entities]
        except SQLAlchemyError as e:
            logger.error(f"查询所有实体数据字典失败: {e}")
            return []
        finally:
            session.close()

    def get_entities_in_area(
        self, min_x: float, max_x: float, min_y: float, max_y: float
    ) -> List[EntityData]:
        """获取指定区域内的实体"""
        session = self.get_session()
        try:
            entities = (
                session.query(EntityData)
                .filter(
                    EntityData.position_x.between(min_x, max_x),
                    EntityData.position_y.between(min_y, max_y),
                )
                .all()
            )
            return entities
        except SQLAlchemyError as e:
            logger.error(f"查询区域实体失败: {e}")
            return []
        finally:
            session.close()

    def get_unknown_entities(self) -> List[UnknownEntity]:
        """获取所有未知实体"""
        session = self.get_session()
        try:
            unknowns = (
                session.query(UnknownEntity)
                .order_by(UnknownEntity.occurrence_count.desc())
                .all()
            )
            return unknowns
        except SQLAlchemyError as e:
            logger.error(f"查询未知实体失败: {e}")
            return []
        finally:
            session.close()

    def get_entities_by_maturity_and_type(
        self,
        min_maturity: int,
        entity_types: Optional[List[str]] = None,
        exclude_unknown: bool = True,
    ) -> List[dict]:
        """根据成熟度和类型获取实体数据

        Args:
            min_maturity: 最小阶数 (1-5)
            entity_types: 实体类型列表，None表示所有类型
            exclude_unknown: 是否排除未知实体
        """
        session = self.get_session()
        try:
            # 构建基础查询 - 直接使用数据库字段
            query = session.query(EntityData).filter(
                EntityData.maturity_level >= min_maturity
            )

            # 排除未知实体
            if exclude_unknown:
                query = query.filter(EntityData.is_unknown.is_(False))

            # 过滤实体类型
            if entity_types:
                query = query.filter(EntityData.entity_type.in_(entity_types))

            # 对于植物类型，额外要求 is_mature = True
            if entity_types and "plant" in entity_types:
                query = query.filter(
                    (EntityData.entity_type != "plant")
                    | (EntityData.entity_type == "plant")
                    & (EntityData.is_mature.is_(True))
                )
            elif not entity_types:
                # 如果没有指定类型，对所有植物要求成熟
                query = query.filter(
                    (EntityData.entity_type != "plant")
                    | (EntityData.entity_type == "plant")
                    & (EntityData.is_mature.is_(True))
                )

            # 执行查询
            entities = query.all()

            logger.debug(f"查询到 {len(entities)} 个满足条件的实体")
            return [entity.to_dict() for entity in entities]

        except SQLAlchemyError as e:
            logger.error(f"查询成熟度实体数据失败: {e}")
            return []
        finally:
            session.close()

    def get_ores_by_maturity(self, min_maturity: int) -> List[dict]:
        """获取指定阶数及以上的矿物"""
        return self.get_entities_by_maturity_and_type(min_maturity, ["ore"], True)

    # 数据清理方法
    def cleanup_data(self) -> bool:
        """清空所有数据"""
        session = self.get_session()
        try:
            # 清理玩家移动数据
            player_deleted = session.query(PlayerMove).delete()

            # 清理实体数据
            entity_deleted = session.query(EntityData).delete()

            # 清理未知实体数据
            unknown_entity_deleted = session.query(UnknownEntity).delete()

            # 清理系统日志
            log_deleted = session.query(SystemLog).delete()

            session.commit()
            logger.info(
                f"数据清空完成: 玩家移动{player_deleted}条, "
                f"实体{entity_deleted}条, 未知实体{unknown_entity_deleted}条, "
                f"日志{log_deleted}条"
            )
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"数据清空失败: {e}")
            return False
        finally:
            session.close()
