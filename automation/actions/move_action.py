from abc import ABC, abstractmethod
from ..context import PlayerPosition


class MoveAction(ABC):
    """移动动作基类"""

    def __init__(self, context, target_position: PlayerPosition, reason: str = ""):
        self.context = context
        self.target_position = target_position
        self.move_reason = reason
        self.move_start_time = None

    @abstractmethod
    def on_arrival(self):
        """到达目的地后的处理"""
        pass

    def execute_move(self) -> bool:
        """执行移动

        Returns:
            bool: 是否到达目的地
        """
        if not self.move_start_time:
            self.move_start_time = self.context.get_state_data("current_time")
            self.context.set_state_data("current_move_reason", self.move_reason)
            self.lo gger.info(f"开始移动: {self.move_reason}")

        # 实现移动逻辑
        if self._check_arrival():
            self.on_arrival()
            self.context.set_state_data("current_move_reason", "")
            return True

        # 执行移动操作
        self._perform_move()
        return False

    def _check_arrival(self) -> bool:
        """检查是否到达目的地"""
        current_pos = self.context.player_position
        target_pos = self.target_position

        # 简单的距离检查
        distance = (
            (current_pos.x - target_pos.x) ** 2 + (current_pos.y - target_pos.y) ** 2
        ) ** 0.5
        return distance < 5.0  # 到达阈值

    def _perform_move(self):
        """执行具体的移动操作"""
        # 调用ADB操作或其他移动逻辑
        # self.context.adb_operations.move_to(self.target_position)
        pass

    def get_move_info(self) -> dict:
        """获取移动信息"""
        return {
            "reason": self.move_reason,
            "target": self.target_position.to_dict(),
            "start_time": self.move_start_time,
        }
