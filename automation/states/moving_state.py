from core.base_state import BaseState
from core.context import GameContext, GameStatus, PlayerPosition
from actions.move_to import MoveTo


class MovingState(BaseState):
    """统一移动状态 - 通过参数区分移动目的"""

    def __init__(self, context: GameContext):
        super().__init__(context)
        self.move_action = None
        self.move_purpose = "explore"  # 默认探索
        self.next_state_after_move = GameStatus.IDLE
        self.move_reason = ""

    def enter(self, **kwargs):
        """进入移动状态"""
        target_position = kwargs.get("target_position")
        if not target_position:
            self.logger.error("移动状态缺少目标位置")
            return

        # 获取移动参数
        self.move_purpose = kwargs.get("purpose", "explore")
        self.next_state_after_move = kwargs.get("next_state", GameStatus.IDLE)
        self.move_reason = kwargs.get("reason", "")

        # 创建移动动作
        self.move_action = MoveTo(self.context, target_position)

        # 设置上下文信息
        self.context.set_move_target(
            target_position, self.move_purpose, self.move_reason
        )

        self.logger.info(f"开始移动: {self.move_reason}")

    def execute(self):
        """移动状态主循环"""
        if not self.move_action:
            self.logger.error("移动动作未初始化")
            return GameStatus.IDLE

        # 执行移动
        move_result = self.move_action.execute()

        if move_result == "arrived":
            # 移动完成，根据目的返回下一个状态
            self.logger.info(f"移动完成: {self.move_reason}")

            if (
                self.move_purpose == "mine"
                and self.next_state_after_move == GameStatus.MINING
            ):
                # 去挖矿：传递矿物信息给挖矿状态
                mineral_info = self.context.get_state_data("mining_target")
                if mineral_info:
                    # 这里可以传递矿物信息给挖矿状态
                    pass
                return GameStatus.MINING
            else:
                # 其他目的：返回指定的下一个状态
                return self.next_state_after_move

        elif move_result == "failed":
            self.logger.error(f"移动失败: {self.move_reason}")
            return GameStatus.IDLE

        return None

    def exit(self):
        """退出移动状态"""
        self.context.clear_move_target()
        self.move_action = None
        self.logger.info("退出移动状态")
