# python ADB_tester.py  n[1]

import subprocess
import time


class ADBTester:
    def __init__(self):
        # 滑动参数配置
        self.start_x = 500  # 起始点x坐标
        self.start_y = 520  # 起始点y坐标
        self.end_x = 500  # 终止点x坐标
        self.end_y = 200  # 终止点y坐标
        self.duration = 150  # 滑动持续时间(毫秒)
        self.swipe_distance = 300  # 滑动距离 (start_y - end_y)

        # 测试记录
        self.test_count = 0
        self.test_results = []

    def adb_swipe(self, start_x, start_y, end_x, end_y, duration):
        """执行ADB滑动命令"""
        cmd = f"adb shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        print(f"执行: {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ADB命令执行失败: {result.stderr}")
                return False
            return True
        except Exception as e:
            print(f"执行ADB命令时出错: {e}")
            return False

    def single_swipe_test(self):
        """执行单次滑动测试"""
        print(f"\n=== 第 {self.test_count + 1} 次滑动测试 ===")
        print(f"起始位置: ({self.start_x}, {self.start_y})")
        print(f"终止位置: ({self.end_x}, {self.end_y})")
        print(f"滑动距离: {self.swipe_distance} 像素")
        print(f"持续时间: {self.duration} 毫秒")

        # 执行滑动
        success = self.adb_swipe(
            self.start_x, self.start_y, self.end_x, self.end_y, self.duration
        )

        if success:
            print("滑动执行成功!")
            # 记录测试结果
            test_result = {
                "test_id": self.test_count + 1,
                "start_x": self.start_x,
                "start_y": self.start_y,
                "end_x": self.end_x,
                "end_y": self.end_y,
                "distance": self.swipe_distance,
                "duration": self.duration,
                "timestamp": time.time(),
            }
            self.test_results.append(test_result)
            self.test_count += 1
        else:
            print("滑动执行失败!")

        return success

    def multiple_swipe_test(self, n):
        """执行多次滑动测试"""
        print(f"\n开始执行 {n} 次滑动测试...")

        for i in range(n):
            if not self.single_swipe_test():
                print(f"第 {i+1} 次测试失败，停止测试")
                break

            # 在多次测试间添加间隔，避免操作过快
            if i < n - 1:
                print("等待2秒后进行下一次测试...")
                time.sleep(2)

        print(f"\n测试完成! 成功执行 {len(self.test_results)} 次滑动")

    def set_swipe_parameters(
        self, start_x=None, start_y=None, end_x=None, end_y=None, duration=None
    ):
        """设置滑动参数"""
        if start_x is not None:
            self.start_x = start_x
        if start_y is not None:
            self.start_y = start_y
        if end_x is not None:
            self.end_x = end_x
        if end_y is not None:
            self.end_y = end_y
        if duration is not None:
            self.duration = duration

        # 更新滑动距离
        self.swipe_distance = abs(self.start_y - self.end_y)

        print("滑动参数已更新:")
        self.show_current_parameters()

    def show_current_parameters(self):
        """显示当前参数设置"""
        print("\n当前滑动参数:")
        print(f"  起始位置: ({self.start_x}, {self.start_y})")
        print(f"  终止位置: ({self.end_x}, {self.end_y})")
        print(f"  滑动距离: {self.swipe_distance} 像素")
        print(f"  持续时间: {self.duration} 毫秒")

    def show_test_summary(self):
        """显示测试摘要"""
        print("\n=== 测试摘要 ===")
        print(f"总测试次数: {len(self.test_results)}")

        if self.test_results:
            print(
                f"测试时间范围: {time.ctime(self.test_results[0]['timestamp'])} - {time.ctime(self.test_results[-1]['timestamp'])}"
            )

            # 显示参数统计
            distances = [r["distance"] for r in self.test_results]
            durations = [r["duration"] for r in self.test_results]

            print(f"滑动距离: {min(distances)} - {max(distances)} 像素")
            print(f"持续时间: {min(durations)} - {max(durations)} 毫秒")

    def interactive_mode(self):
        """交互式测试模式"""
        print("=== ADB滑动测试程序 ===")
        print("命令说明:")
        print("  n [次数] - 执行n次滑动测试")
        print("  s - 显示当前参数")
        print("  p - 设置滑动参数")
        print("  r - 显示测试结果")
        print("  q - 退出程序")

        while True:
            try:
                user_input = input("\n请输入命令: ").strip().lower()

                if user_input == "q":
                    print("退出程序")
                    break

                elif user_input == "s":
                    self.show_current_parameters()

                elif user_input == "p":
                    self.set_parameters_interactive()

                elif user_input == "r":
                    self.show_test_summary()

                elif user_input.startswith("n"):
                    # 解析测试次数
                    parts = user_input.split()
                    if len(parts) == 1:
                        n = 1
                    else:
                        try:
                            n = int(parts[1])
                        except ValueError:
                            print("错误: 请输入有效的测试次数")
                            continue

                    if n > 0:
                        self.multiple_swipe_test(n)
                    else:
                        print("错误: 测试次数必须大于0")

                else:
                    print("未知命令，请使用: n, s, p, r, q")

            except KeyboardInterrupt:
                print("\n程序被用户中断")
                break
            except Exception as e:
                print(f"发生错误: {e}")

    def set_parameters_interactive(self):
        """交互式设置参数"""
        print("\n设置滑动参数 (直接回车保持当前值):")

        try:
            new_start_x = input(f"起始X坐标 (当前: {self.start_x}): ")
            if new_start_x:
                self.start_x = int(new_start_x)

            new_start_y = input(f"起始Y坐标 (当前: {self.start_y}): ")
            if new_start_y:
                self.start_y = int(new_start_y)

            new_end_x = input(f"终止X坐标 (当前: {self.end_x}): ")
            if new_end_x:
                self.end_x = int(new_end_x)

            new_end_y = input(f"终止Y坐标 (当前: {self.end_y}): ")
            if new_end_y:
                self.end_y = int(new_end_y)

            new_duration = input(f"滑动持续时间(毫秒) (当前: {self.duration}): ")
            if new_duration:
                self.duration = int(new_duration)

            # 更新距离
            self.swipe_distance = abs(self.start_y - self.end_y)

            print("参数设置完成!")
            self.show_current_parameters()

        except ValueError:
            print("错误: 请输入有效的数字")
        except Exception as e:
            print(f"设置参数时出错: {e}")


def main():
    # 检查ADB是否可用
    try:
        result = subprocess.run(
            "adb devices", shell=True, capture_output=True, text=True
        )
        if "device" not in result.stdout:
            print("警告: 未检测到已连接的ADB设备")
            print("请确保:")
            print("1. 已开启USB调试")
            print("2. 已授权此电脑")
            print("3. ADB已添加到系统PATH")

            continue_anyway = input("是否继续? (y/n): ").lower()
            if continue_anyway != "y":
                return
    except Exception as e:
        print(f"检查ADB时出错: {e}")
        print("请确保ADB已正确安装")
        return

    tester = ADBTester()
    tester.interactive_mode()


if __name__ == "__main__":
    main()
