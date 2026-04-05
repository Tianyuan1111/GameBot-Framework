import time
from ..core.base_state import BaseState
from ..core.context import GameStatus
from ..actions.mining import MiningAction


class MiningState(BaseState):
    """挖矿状态"""

    def __init__(self, context):
        super().__init__(context)
        self.mining_action = MiningAction()
        self.mining_complete = False

    def enter(self, **kwargs) -> None:
        self.context.set_state(GameStatus.MINING)
        self.context.set_mining_status(True)
        self.mining_complete = False
        target = self.context.get_state_data("selected_target")
        print(f"开始挖矿: {target['type'] if target else '未知矿物'}")

    def execute(self) -> GameStatus:
        if self.mining_complete:
            print("挖矿完成，继续扫描")
            return GameStatus.MAP_SCANNING

        # 执行挖矿动作
        success = self.mining_action.mine()

        if success:
            self.mining_complete = True
            # 更新玩家坐标（挖矿后可能微调位置）
            # self.context.update_position(new_x, new_y)
        else:
            print("挖矿失败，重新扫描")
            return GameStatus.MAP_SCANNING

        return None

    def exit(self) -> None:
        self.context.set_mining_status(False)
        print("挖矿状态结束")
