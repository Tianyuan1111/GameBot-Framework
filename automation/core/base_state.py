from abc import ABC, abstractmethod
from typing import Optional
from .context import GameContext, GameStatus


class BaseState(ABC):
    """状态基类，定义统一接口"""

    def __init__(self, context: GameContext):
        self.context = context
        self.state_name = self.__class__.__name__

    @abstractmethod
    def enter(self, **kwargs) -> None:
        """进入状态时的处理"""
        pass

    @abstractmethod
    def execute(self) -> Optional[GameStatus]:
        """状态执行逻辑

        Returns:
            返回下一个状态，如果返回None则保持当前状态
        """
        pass

    @abstractmethod
    def exit(self) -> None:
        """退出状态时的处理"""
        pass

    def can_enter(self) -> bool:
        """检查是否可以进入该状态"""
        return True

    def can_exit(self) -> bool:
        """检查是否可以退出该状态"""
        return True

    def handle_exception(self, exception: Exception) -> Optional[GameStatus]:
        """处理状态执行中的异常

        Returns:
            返回异常处理后的状态，None表示保持当前状态
        """
        print(f"状态 {self.state_name} 发生异常: {exception}")
        return None
