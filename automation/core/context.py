import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class GameStatus(Enum):
    """游戏状态枚举"""

    IDLE = "idle"  # 空闲状态（初始状态）
    MAP_SCANNING = "map_scanning"  # 地图扫描
    # TARGET_SELECTING = "target_selecting"  # 目标选择
    # MOVING_TO_TARGET = "moving_to_target"  # 移动到目标
    # MAP_TRANSITION = "map_transition"  # 地图切换
    # ERROR_RECOVERY = "error_recovery"  # 错误恢复


@dataclass
class PlayerPosition:
    """玩家坐标"""

    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


class GameContext:
    """游戏上下文，用于状态间数据共享"""

    def __init__(self):
        # 状态相关
        self.current_state = GameStatus.IDLE
        self.target_state = GameStatus.IDLE

        # 玩家信息
        self.player_position = PlayerPosition()
        self.is_mining = False
        self.mining_target = None

        # 控制标志
        self._running = True
        self._paused = False
        self._lock = threading.RLock()

        # 状态数据缓存
        self._state_data = {}

    def update_position(self, x: float, y: float):
        """更新玩家坐标"""
        with self._lock:
            self.player_position.x = x
            self.player_position.y = y

    def set_mining_status(self, is_mining: bool, target: Optional[str] = None):
        """设置挖矿状态"""
        with self._lock:
            self.is_mining = is_mining
            self.mining_target = target

    def set_state(self, state: GameStatus):
        """设置当前状态"""
        with self._lock:
            self.current_state = state

    def set_target_state(self, state: GameStatus):
        """设置目标状态"""
        with self._lock:
            self.target_state = state

    def pause(self):
        """暂停状态机"""
        with self._lock:
            self._paused = True

    def resume(self):
        """恢复状态机"""
        with self._lock:
            self._paused = False

    def stop(self):
        """停止状态机"""
        with self._lock:
            self._running = False

    @property
    def running(self) -> bool:
        """状态机是否运行中"""
        with self._lock:
            return self._running

    @property
    def paused(self) -> bool:
        """状态机是否暂停"""
        with self._lock:
            return self._paused

    def set_state_data(self, key: str, value: Any):
        """设置状态数据"""
        with self._lock:
            self._state_data[key] = value

    def get_state_data(self, key: str, default: Any = None) -> Any:
        """获取状态数据"""
        with self._lock:
            return self._state_data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于网页展示"""
        with self._lock:
            return {
                "current_state": self.current_state.value,
                "target_state": self.target_state.value,
                "player_position": self.player_position.to_dict(),
                "is_mining": self.is_mining,
                "mining_target": self.mining_target,
                "running": self._running,
                "paused": self._paused,
                "timestamp": time.time(),
            }
