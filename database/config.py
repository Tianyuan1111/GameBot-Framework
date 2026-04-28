# database/config.py

import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置类"""

    def __init__(self, db_path: str = "game_data.db"):
        self.db_path = db_path
        self.engine = None
        self.SessionLocal: Optional[sessionmaker] = None
        # 初始化时就创建引擎
        self.init_engine()

    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        return f"sqlite:///{self.db_path}"

    def init_engine(self):
        """初始化数据库引擎"""
        try:
            connection_string = self.get_connection_string()
            self.engine = create_engine(
                connection_string,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,  # 设为 True 可以查看所有 SQL 语句
            )
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
            logger.info(f"数据库引擎初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库引擎初始化失败: {e}")
            raise

    def get_session(self) -> Session:
        """获取数据库会话"""
        if self.SessionLocal is None:
            raise RuntimeError("数据库未正确初始化")
        return self.SessionLocal()


# 全局数据库配置实例
db_config = DatabaseConfig()
