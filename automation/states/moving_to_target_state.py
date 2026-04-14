import time
from ..core.base_state import BaseState
from ..core.context import GameStatus
from ..actions.move_to import MoveToAction


class MovingToTargetState(BaseState):
    """移动到目标状态"""

    def __init__(self, context):
        super().__init__(context)
        self.move_action = MoveToAction()
        self.move_complete = False

    def enter(self, **kwargs) -> None:
        self.context.set_state(GameStatus.MOVING_TO_TARGET)
        self.move_complete = False
        target = self.context.get_state_data("selected_target")
        if target:
            print(f"开始移动到目标: {target['position']}")
        else:
            print("移动目标未设置")

    def execute(self) -> GameStatus:
        if self.move_complete:
            print("移动完成，开始挖矿")
            return GameStatus.MINING

        target = self.context.get_state_data("selected_target")
        if not target:
            print("错误：移动目标丢失")
            return GameStatus.TARGET_SELECTING

        # 执行移动动作
        success = self.move_action.move_to(target["position"])

        if success:
            self.move_complete = True
        else:
            print("移动失败，重新选择目标")
            return GameStatus.TARGET_SELECTING

        return None

    def exit(self) -> None:
        print("移动状态结束")
