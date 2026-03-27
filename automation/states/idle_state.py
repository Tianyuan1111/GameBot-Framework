from typing import Optional
import time
from ..core.base_state import BaseState
from ..core.context import GameStatus


class IdleState(BaseState):
    """空闲状态 - 等待网页控制命令"""

    def enter(self, **kwargs) -> None:
        self.context.set_state(GameStatus.IDLE)
        self.context.set_mining_status(False)
        print("进入空闲状态，等待开始命令...")

    def execute(self) -> Optional[GameStatus]:
        # 检查是否有目标状态（由网页控制设置）
        if self.context.target_state != GameStatus.IDLE:
            return self.context.target_state

        time.sleep(0.5)  # 降低CPU占用
        return None

    def exit(self) -> None:
        print("退出空闲状态")
