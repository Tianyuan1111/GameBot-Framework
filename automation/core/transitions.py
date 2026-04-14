from typing import Dict, Callable, Any
from .context import GameContext, GameStatus


class StateTransitions:
    """状态转移条件管理"""

    def __init__(self, context: GameContext):
        self.context = context
        self._transitions: Dict[GameStatus, Dict[GameStatus, Callable]] = {}

        # 初始化转移条件
        self._initialize_transitions()

    def _initialize_transitions(self):
        """初始化状态转移条件"""
        # 从空闲状态可以转移到扫描状态
        self.add_transition(
            GameStatus.IDLE, GameStatus.MAP_SCANNING, self._can_start_scanning
        )

        # 从扫描状态可以转回空闲状态
        self.add_transition(
            GameStatus.MAP_SCANNING, GameStatus.IDLE, self._can_return_to_idle
        )

        # 扫描状态也可以转移到目标选择（先注释掉）
        # self.add_transition(
        #     GameStatus.MAP_SCANNING,
        #     GameStatus.TARGET_SELECTING,
        #     self._can_select_target
        # )

    def add_transition(
        self,
        from_state: GameStatus,
        to_state: GameStatus,
        condition: Callable[[], bool],
    ) -> None:
        """添加状态转移条件"""
        if from_state not in self._transitions:
            self._transitions[from_state] = {}

        self._transitions[from_state][to_state] = condition

    def can_transition(self, from_state: GameStatus, to_state: GameStatus) -> bool:
        """检查是否可以从一个状态转移到另一个状态"""
        if from_state not in self._transitions:
            return False

        if to_state not in self._transitions[from_state]:
            return False

        condition = self._transitions[from_state][to_state]
        return condition()

    def get_available_transitions(self, from_state: GameStatus) -> list[GameStatus]:
        """获取从当前状态可用的转移目标"""
        if from_state not in self._transitions:
            return []

        available = []
        for to_state, condition in self._transitions[from_state].items():
            if condition():
                available.append(to_state)

        return available

    # 转移条件函数
    def _can_start_scanning(self) -> bool:
        """是否可以开始扫描"""
        # 只要目标状态是扫描状态，就可以开始扫描
        return self.context.target_state == GameStatus.MAP_SCANNING

    def _can_return_to_idle(self) -> bool:
        """是否可以返回空闲状态"""
        # 扫描完成后可以返回空闲状态
        scan_complete = self.context.get_state_data("scan_complete", False)
        return scan_complete or self.context.target_state == GameStatus.IDLE

    # 先注释掉其他转移条件
    # def _can_select_target(self) -> bool:
    #     """是否可以选择目标"""
    #     minerals_found = self.context.get_state_data("minerals_found", [])
    #     return len(minerals_found) > 0
