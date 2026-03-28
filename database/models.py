# database/models.py

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

# 创建 SQLAlchemy 声明式基类
# 所有数据库模型类都需要继承这个 Base 类
# 这样 SQLAlchemy 才能知道哪些类需要映射到数据库表
Base = declarative_base()


class PlayerMove(Base):
    """玩家移动数据表"""

    __tablename__ = "player_moves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    velocity_x = Column(Float, nullable=True)
    velocity_y = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    packet_source = Column(String(50), nullable=True)

    def to_dict(self):
        """转换为字典"""
        timestamp_value = getattr(self, "timestamp", None)
        return {
            "id": self.id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "timestamp": timestamp_value.isoformat() if timestamp_value else None,
            "packet_source": self.packet_source,
        }


class CameraMove(Base):
    """视角移动数据表"""

    __tablename__ = "camera_moves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    angle_x = Column(Float, nullable=False)  # X轴角度
    angle_y = Column(Float, nullable=False)  # Y轴角度
    delta_x = Column(Float, nullable=True)  # X轴角度变化量
    delta_y = Column(Float, nullable=True)  # Y轴角度变化量
    timestamp = Column(DateTime, default=datetime.now)
    packet_source = Column(String(50), nullable=True)

    def to_dict(self):
        """转换为字典"""
        timestamp_value = getattr(self, "timestamp", None)
        return {
            "id": self.id,
            "angle_x": self.angle_x,
            "angle_y": self.angle_y,
            "delta_x": self.delta_x,
            "delta_y": self.delta_y,
            "timestamp": timestamp_value.isoformat() if timestamp_value else None,
            "packet_source": self.packet_source,
        }


class EntityData(Base):
    """实体数据表（植物、矿物等）"""

    __tablename__ = "entity_data"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 序列id
    entity_id = Column(Integer, nullable=False, index=True)  # 3020021
    entity_type = Column(String(20), nullable=False, index=True)  # plant, ore, unknown
    entity_name = Column(String(100), nullable=False)  # 聚灵草
    category = Column(String(50), nullable=False)  # 植物/矿物种类数字 002
    growth_stage = Column(Integer, nullable=True)  # 植物生长阶段 1-5
    is_mature = Column(Boolean, default=False, index=True)  # 新增：是否成熟
    maturity_level = Column(Integer, nullable=False, index=True)  # 新增：实体阶数 1-5
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    entity_index = Column(String(50), nullable=True)
    is_unknown = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now)
    raw_data = Column(Text, nullable=True)  # 原始数据，用于调试

    def to_dict(self):
        """转换为字典"""
        timestamp_value = getattr(self, "timestamp", None)
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "category": self.category,
            "growth_stage": self.growth_stage,
            "maturity_level": self.maturity_level,  # 新增
            "is_mature": self.is_mature,  # 新增
            "position_x": self.position_x,
            "position_y": self.position_y,
            "entity_index": self.entity_index,
            "is_unknown": self.is_unknown,
            "timestamp": timestamp_value.isoformat() if timestamp_value else None,
            "raw_data": self.raw_data,
        }


class UnknownEntity(Base):
    """未知实体记录表，用于后续分析"""

    __tablename__ = "unknown_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, nullable=False, index=True)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    raw_hex_data = Column(Text, nullable=True)
    occurrence_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)

    def to_dict(self):
        """转换为字典"""
        first_seen_value = getattr(self, "first_seen", None)
        last_seen_value = getattr(self, "last_seen", None)
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "raw_hex_data": self.raw_hex_data,
            "occurrence_count": self.occurrence_count,
            "first_seen": first_seen_value.isoformat() if first_seen_value else None,
            "last_seen": last_seen_value.isoformat() if last_seen_value else None,
        }


class SystemLog(Base):
    """系统日志表"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    module = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

    def to_dict(self):
        """转换为字典"""
        timestamp_value = getattr(self, "timestamp", None)
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "module": self.module,
            "timestamp": timestamp_value.isoformat() if timestamp_value else None,
        }
