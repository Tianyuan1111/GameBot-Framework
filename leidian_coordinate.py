# python leidian_coordinate.py
import subprocess
from datetime import datetime


class StableClickDetector:
    def __init__(self, device_index=0):
        self.device_index = device_index
        self.device_name = f"emulator-{5554 + device_index * 2}"
        # 默认屏幕尺寸（雷电模拟器常用尺寸）
        self.screen_width = 1080
        self.screen_height = 1920
        self.event_count = 0

    def check_adb_connection(self):
        """检查ADB连接"""
        try:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, check=True
            )
            if self.device_name in result.stdout:
                print(f"✓ 找到设备: {self.device_name}")
                return True
            else:
                print(f"✗ 未找到设备: {self.device_name}")
                print("请确保:")
                print("1. 雷电模拟器正在运行")
                print("2. ADB已正确连接")
                print("3. 设备索引正确")
                return False
        except Exception as e:
            print(f"ADB检查失败: {e}")
            return False

    def parse_hex_coordinate(self, hex_str):
        """解析16进制坐标值"""
        try:
            return int(hex_str, 16)
        except ValueError:
            return None

    def get_relative_position(self, x, y):
        """计算相对位置百分比"""
        x_percent = (x / self.screen_width) * 100
        y_percent = (y / self.screen_height) * 100
        return x_percent, y_percent

    def monitor_touches_simple(self):
        """简化的触摸监控 - 带坐标解析"""
        if not self.check_adb_connection():
            return

        print(f"开始监控雷电模拟器 {self.device_index} 的点击事件...")
        print("屏幕尺寸:", f"{self.screen_width}x{self.screen_height}")
        print("按下 Ctrl+C 停止监控")
        print("-" * 50)

        process = None
        try:
            process = subprocess.Popen(
                ["adb", "-s", self.device_name, "shell", "getevent", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            if process.stdout is None:
                print("错误: 无法获取命令输出流，ADB命令可能执行失败")
                if process.stderr:
                    error_output = process.stderr.read()
                    print(f"错误详情: {error_output}")
                return

            # 用于存储当前触摸事件的数据
            touch_data = {}
            self.event_count = 0

            while True:
                line = process.stdout.readline()
                if not line:  # 空字符串表示流结束
                    break

                line = line.strip()
                if not line:
                    continue

                # 解析X坐标
                if "ABS_MT_POSITION_X" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        hex_value = parts[-1]
                        x = self.parse_hex_coordinate(hex_value)
                        if x is not None:
                            touch_data["x"] = x
                            touch_data["x_hex"] = hex_value

                # 解析Y坐标
                elif "ABS_MT_POSITION_Y" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        hex_value = parts[-1]
                        y = self.parse_hex_coordinate(hex_value)
                        if y is not None:
                            touch_data["y"] = y
                            touch_data["y_hex"] = hex_value

                # 当收集到完整的坐标数据时输出
                if "x" in touch_data and "y" in touch_data:
                    self.event_count += 1
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    x, y = touch_data["x"], touch_data["y"]
                    x_percent, y_percent = self.get_relative_position(x, y)

                    print(f"[{timestamp}] 事件#{self.event_count}")
                    print(f"   坐标: ({x}, {y})")
                    print(f"   相对位置: ({x_percent:.1f}%, {y_percent:.1f}%)")
                    print(
                        f"   原始数据: X={touch_data['x_hex']}, Y={touch_data['y_hex']}"
                    )
                    print("-" * 50)

                    # 重置数据，等待下一组坐标
                    touch_data = {}

        except KeyboardInterrupt:
            print(f"\n总共捕获 {self.event_count} 个触摸事件")
            print("停止监控...")
        except Exception as e:
            print(f"监控过程中出现错误: {e}")
            if process and process.stderr:
                try:
                    stderr_output = process.stderr.read()
                    if stderr_output:
                        print(f"ADB错误输出: {stderr_output}")
                except Exception:
                    pass
        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()

    def monitor_touches_advanced(self):
        """高级触摸监控 - 包含滑动轨迹检测"""
        if not self.check_adb_connection():
            return

        print(f"开始高级监控雷电模拟器 {self.device_index} 的触摸事件...")
        print("屏幕尺寸:", f"{self.screen_width}x{self.screen_height}")
        print("按下 Ctrl+C 停止监控")
        print("-" * 50)

        process = None
        try:
            process = subprocess.Popen(
                ["adb", "-s", self.device_name, "shell", "getevent", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            if process.stdout is None:
                print("错误: 无法获取命令输出流")
                return

            # 用于跟踪触摸序列
            touch_sequence = []
            current_touch = {}

            while True:
                line = process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # 检测触摸开始 (ABS_MT_TRACKING_ID)
                if "ABS_MT_TRACKING_ID" in line and "ffffffff" not in line:
                    if current_touch and touch_sequence:
                        self._print_touch_sequence(touch_sequence)
                    touch_sequence = []
                    current_touch = {}
                    continue

                # 检测触摸结束 (ABS_MT_TRACKING_ID 为 -1)
                if "ABS_MT_TRACKING_ID" in line and "ffffffff" in line:
                    if current_touch and touch_sequence:
                        self._print_touch_sequence(touch_sequence)
                    touch_sequence = []
                    current_touch = {}
                    continue

                # 解析坐标
                if "ABS_MT_POSITION_X" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        hex_value = parts[-1]
                        x = self.parse_hex_coordinate(hex_value)
                        if x is not None:
                            current_touch["x"] = x
                            current_touch["x_hex"] = hex_value

                elif "ABS_MT_POSITION_Y" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        hex_value = parts[-1]
                        y = self.parse_hex_coordinate(hex_value)
                        if y is not None:
                            current_touch["y"] = y
                            current_touch["y_hex"] = hex_value

                # 当收集到完整坐标时添加到序列
                if "x" in current_touch and "y" in current_touch:
                    current_touch["timestamp"] = datetime.now()
                    touch_sequence.append(current_touch.copy())
                    current_touch = {}

        except KeyboardInterrupt:
            print("\n停止高级监控...")
        except Exception as e:
            print(f"高级监控过程中出现错误: {e}")
        finally:
            if process:
                process.terminate()

    def _print_touch_sequence(self, sequence):
        """打印触摸序列"""
        if not sequence:
            return

        print(f"\n🎯 触摸序列 (共{len(sequence)}个点)")
        start_time = sequence[0]["timestamp"]

        for i, point in enumerate(sequence):
            time_diff = (point["timestamp"] - start_time).total_seconds() * 1000
            x_percent, y_percent = self.get_relative_position(point["x"], point["y"])

            print(
                f"  #{i+1:02d} [+{time_diff:6.1f}ms] "
                f"坐标: ({point['x']:4d}, {point['y']:4d}) "
                f"位置: ({x_percent:5.1f}%, {y_percent:5.1f}%)"
            )

        # 如果是滑动，显示轨迹信息
        if len(sequence) > 1:
            start_point = sequence[0]
            end_point = sequence[-1]
            dx = end_point["x"] - start_point["x"]
            dy = end_point["y"] - start_point["y"]
            duration = (
                end_point["timestamp"] - start_point["timestamp"]
            ).total_seconds() * 1000

            print(f"  📊 轨迹: ΔX={dx:+.1f}, ΔY={dy:+.1f}, 时长: {duration:.1f}ms")


# 使用示例
if __name__ == "__main__":
    detector = StableClickDetector(device_index=0)

    print("选择监控模式:")
    print("1. 简单模式 (显示点击坐标)")
    print("2. 高级模式 (显示滑动轨迹)")

    choice = input("请选择模式 (1 或 2): ").strip()

    if choice == "2":
        detector.monitor_touches_advanced()
    else:
        detector.monitor_touches_simple()
