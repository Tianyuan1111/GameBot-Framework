import threading
import time
import logging
from typing import Dict, Type, Optional
from .context import GameContext, GameStatus
from .base_state import BaseState
from .transitions import StateTransitions


class StateMachine:
    """状态机主框架 - 支持及时响应控制"""

    def __init__(self):
        self.context = GameContext()
        self.transitions = StateTransitions(self.context)

        # 状态注册表
        self._states: Dict[GameStatus, Type[BaseState]] = {}
        self._current_state_instance: Optional[BaseState] = None

        # 线程控制
        self._state_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._control_thread: Optional[threading.Thread] = None
        self._state_thread_running = False
        self._monitor_thread_running = False
        self._control_thread_running = False

        # 控制信号
        self._control_signal = threading.Event()
        self._state_change_requested = False
        self._requested_state: Optional[GameStatus] = None

        # 日志
        self.logger = logging.getLogger("StateMachine")

    def register_state(self, state_enum: GameStatus, state_class: Type[BaseState]):
        """注册状态"""
        self._states[state_enum] = state_class

    def start(self):
        """启动状态机"""
        if not self._states:
            raise ValueError("没有注册任何状态")

        self.context.set_state(GameStatus.IDLE)
        self.context.set_target_state(GameStatus.IDLE)

        # 启动状态循环线程
        self._state_thread_running = True
        self._state_thread = threading.Thread(target=self._state_loop, name="StateLoop")
        self._state_thread.daemon = True
        self._state_thread.start()

        # 启动监控线程
        self._monitor_thread_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="MonitorLoop"
        )
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

        # 启动控制响应线程
        self._control_thread_running = True
        self._control_thread = threading.Thread(
            target=self._control_loop, name="ControlLoop"
        )
        self._control_thread.daemon = True
        self._control_thread.start()

        self.logger.info("状态机启动")

    def stop(self):
        """停止状态机"""
        self.logger.info("正在停止状态机...")

        self.context.stop()
        self._state_thread_running = False
        self._monitor_thread_running = False
        self._control_thread_running = False

        # 通知所有线程退出
        self._control_signal.set()

        if self._state_thread and self._state_thread.is_alive():
            self._state_thread.join(timeout=5)

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)

        if self._control_thread and self._control_thread.is_alive():
            self._control_thread.join(timeout=5)

        self.logger.info("状态机已停止")

    def _state_loop(self):
        """状态循环 - 使用短时间间隔确保及时响应控制"""
        self.logger.info("状态循环线程启动")

        while self._state_thread_running and self.context.running:
            try:
                # 检查是否暂停
                if self.context.paused:
                    time.sleep(0.1)
                    continue

                current_state_enum = self.context.current_state

                # 获取当前状态实例
                if (
                    not self._current_state_instance
                    or self._current_state_instance.__class__
                    != self._states.get(current_state_enum)
                ):

                    if self._current_state_instance:
                        self._current_state_instance.exit()

                    state_class = self._states.get(current_state_enum)
                    if state_class:
                        self._current_state_instance = state_class(self.context)
                        self._current_state_instance.enter()

                # 执行当前状态（使用短时间间隔）
                if self._current_state_instance:
                    # 检查是否有控制信号
                    if self._control_signal.is_set():
                        self._control_signal.clear()
                        self.logger.debug("状态循环收到控制信号")

                    # 执行状态逻辑，但限制单次执行时间
                    start_time = time.time()
                    next_state = self._current_state_instance.execute()
                    execution_time = time.time() - start_time

                    # 如果状态执行时间过长，记录警告
                    if execution_time > 1.0:
                        self.logger.warning(
                            f"状态 {current_state_enum.value} 执行时间过长: {execution_time:.2f}秒"
                        )

                    # 检查状态转移
                    if next_state and next_state != current_state_enum:
                        if self.transitions.can_transition(
                            current_state_enum, next_state
                        ):
                            self.context.set_state(next_state)
                            self.logger.info(
                                f"状态转移: {current_state_enum.value} -> {next_state.value}"
                            )

                # 使用较短的睡眠时间，提高响应性
                time.sleep(0.01)  # 10ms间隔，确保及时响应控制

            except Exception as e:
                self.logger.error(f"状态循环异常: {e}")
                if self._current_state_instance:
                    next_state = self._current_state_instance.handle_exception(e)
                    if next_state:
                        self.context.set_state(next_state)
                time.sleep(0.1)  # 异常后短暂等待

        self.logger.info("状态循环线程结束")

    def _monitor_loop(self):
        """监控循环 - 监控异常状态和控制状态转移"""
        self.logger.info("监控循环线程启动")

        while self._monitor_thread_running and self.context.running:
            try:
                # 检查异常情况
                self._check_emergency_conditions()

                # 检查是否需要强制状态转移
                self._check_forced_transitions()

                time.sleep(0.5)  # 监控频率较低

            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                time.sleep(1)

        self.logger.info("监控循环线程结束")

    def _control_loop(self):
        """控制响应循环 - 专门处理控制信号"""
        self.logger.info("控制响应线程启动")

        while self._control_thread_running and self.context.running:
            try:
                # 检查是否有状态变更请求
                if self._state_change_requested and self._requested_state is not None:
                    current_state = self.context.current_state
                    requested_state = self._requested_state

                    if self.transitions.can_transition(current_state, requested_state):
                        self.context.set_state(requested_state)
                        self.context.set_target_state(requested_state)
                        self.logger.info(
                            f"控制线程触发状态转移: {current_state.value} -> {requested_state.value}"
                        )
                    else:
                        self.logger.warning(
                            f"控制线程: 无法从 {current_state.value} 转移到 {requested_state.value}"
                        )

                    # 重置请求
                    self._state_change_requested = False
                    self._requested_state = None

                # 发送控制信号到状态循环
                self._control_signal.set()

                time.sleep(0.1)  # 控制循环频率较高

            except Exception as e:
                self.logger.error(f"控制循环异常: {e}")
                time.sleep(0.5)

        self.logger.info("控制响应线程结束")

    def _check_emergency_conditions(self):
        """检查紧急情况"""
        # TODO: 实现具体的异常检测逻辑
        # 例如：游戏崩溃、网络断开、角色死亡等

        # 示例：检查是否需要紧急停止
        if self.context.get_state_data("emergency_stop", False):
            self.logger.warning("检测到紧急情况，停止状态机")
            self.stop()

    def _check_forced_transitions(self):
        """检查强制状态转移"""
        # 如果目标状态与当前状态不同，且允许转移，则进行转移
        current_state = self.context.current_state
        target_state = self.context.target_state

        if current_state != target_state and self.transitions.can_transition(
            current_state, target_state
        ):
            self.context.set_state(target_state)
            self.logger.info(
                f"强制状态转移: {current_state.value} -> {target_state.value}"
            )

    # Web控制接口 - 这些方法会立即被控制线程处理
    def set_target_state_from_web(self, state: str) -> bool:
        """从网页设置目标状态"""
        try:
            target_state = GameStatus(state)

            # 设置目标状态（用于正常状态转移）
            self.context.set_target_state(target_state)

            # 同时发送立即状态变更请求
            self._requested_state = target_state
            self._state_change_requested = True

            self.logger.info(f"网页控制: 设置目标状态为 {state}")
            return True
        except ValueError:
            self.logger.error(f"网页控制: 无效的状态 {state}")
            return False

    def force_state_change_from_web(self, state: str) -> bool:
        """从网页强制立即切换状态（忽略转移条件）"""
        try:
            target_state = GameStatus(state)
            current_state = self.context.current_state

            # 强制立即切换状态
            self.context.set_state(target_state)
            self.context.set_target_state(target_state)

            self.logger.info(
                f"网页强制控制: {current_state.value} -> {target_state.value}"
            )
            return True
        except ValueError:
            self.logger.error(f"网页强制控制: 无效的状态 {state}")
            return False

    def pause_from_web(self):
        """从网页暂停状态机"""
        self.context.pause()
        self._control_signal.set()  # 通知状态循环
        self.logger.info("网页控制: 暂停状态机")

    def resume_from_web(self):
        """从网页恢复状态机"""
        self.context.resume()
        self._control_signal.set()  # 通知状态循环
        self.logger.info("网页控制: 恢复状态机")

    def emergency_stop_from_web(self):
        """从网页紧急停止"""
        self.context.set_state_data("emergency_stop", True)
        self._control_signal.set()  # 通知状态循环
        self.logger.warning("网页控制: 紧急停止")

    def get_status_for_web(self) -> dict:
        """获取状态信息用于网页展示"""
        status = self.context.to_dict()

        # 添加额外的状态机信息
        status.update(
            {
                "state_thread_alive": (
                    self._state_thread.is_alive() if self._state_thread else False
                ),
                "monitor_thread_alive": (
                    self._monitor_thread.is_alive() if self._monitor_thread else False
                ),
                "control_thread_alive": (
                    self._control_thread.is_alive() if self._control_thread else False
                ),
                "control_signal_pending": self._control_signal.is_set(),
            }
        )

        return status
