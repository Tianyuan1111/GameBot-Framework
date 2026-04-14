import subprocess
from typing import Tuple, Optional


class ADBOperation:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.adb_cmd = "adb"
        if device_id:
            self.adb_cmd = f"adb -s {device_id}"

    def execute_adb(self, command: str) -> bool:
        """执行ADB命令"""
        try:
            full_command = f"{self.adb_cmd} {command}"
            result = subprocess.run(
                full_command, shell=True, capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"ADB命令执行失败: {e}")
            return False

    def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int
    ) -> bool:
        """滑动屏幕"""
        command = f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        return self.execute_adb(command)

    def tap(self, x: int, y: int) -> bool:
        """点击屏幕"""
        command = f"shell input tap {x} {y}"
        return self.execute_adb(command)

    def key_event(self, key_code: int) -> bool:
        """发送按键事件"""
        command = f"shell input keyevent {key_code}"
        return self.execute_adb(command)

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            command = f"{self.adb_cmd} shell wm size"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # 解析输出格式: "Physical size: 1080x1920"
                size_str = result.stdout.strip().split(": ")[-1].split("x")
                return int(size_str[0]), int(size_str[1])
        except Exception as e:
            print(f"获取屏幕尺寸失败: {e}")
        return 1080, 1920  # 默认尺寸


# 全局ADB实例
adb = ADBOperation()
