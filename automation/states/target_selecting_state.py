from ..core.base_state import BaseState
from ..core.context import GameStatus


class TargetSelectingState(BaseState):
    """目标选择状态 - 从矿物数据库中选择最优目标"""

    def enter(self, **kwargs) -> None:
        self.context.set_state(GameStatus.TARGET_SELECTING)
        self.selected_target = None
        print("开始选择目标矿物...")

    def execute(self) -> GameStatus:
        minerals = self.context.get_state_data("minerals_found", [])

        if not minerals:
            print("没有可选的矿物")
            return GameStatus.MAP_SCANNING

        # 选择最优目标
        self.selected_target = self._select_best_target(minerals)

        if self.selected_target:
            print(
                f"选择目标: {self.selected_target['type']} 在位置 {self.selected_target['position']}"
            )
            return GameStatus.MOVING_TO_TARGET
        else:
            print("没有合适的目标")
            return GameStatus.MAP_SCANNING

    def _select_best_target(self, minerals):
        """从矿物列表中选择最优目标"""
        if not minerals:
            return None

        # 简单的选择策略：选择距离最近的矿物
        best_target = min(minerals, key=lambda x: x.get("distance", float("inf")))

        # TODO: 可以添加更复杂的选择逻辑，比如：
        # - 考虑矿物类型优先级
        # - 考虑路径复杂度
        # - 考虑当前背包空间等

        return best_target

    def exit(self) -> None:
        # 保存选择的目标到上下文
        if self.selected_target:
            self.context.set_state_data("selected_target", self.selected_target)
            self.context.set_mining_status(False, self.selected_target["type"])
