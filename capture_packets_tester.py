# capture_packets_tester.py
# 使用sudo python capture_packets_tester.py运行（如果要权限）
# check_capture_robust.py

import os
import sys
import threading
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def safe_import_config():
    """安全导入配置，处理可能的导入错误"""
    try:
        from config.settings import (
            CLIENT_PORTS,
            ENABLE_PORT_FILTER,
            INTERFACE,
            PACKET_LENGTHS,
            SERVER_IP,
        )

        return {
            "SERVER_IP": SERVER_IP,
            "CLIENT_PORTS": CLIENT_PORTS,
            "INTERFACE": INTERFACE,
            "PACKET_LENGTHS": PACKET_LENGTHS,
            "ENABLE_PORT_FILTER": ENABLE_PORT_FILTER,
        }
    except ImportError as e:
        print(f"❌ 导入配置失败: {e}")
        print("请检查 config/settings.py 文件是否存在且格式正确")
        return None


def safe_import_capture():
    """安全导入捕获模块"""
    try:
        from capture.capture_packets import packet_queue, process_packet, start_sniff

        return packet_queue, start_sniff, process_packet
    except ImportError as e:
        print(f"❌ 导入捕获模块失败: {e}")
        print("请检查 capture/capture_packets.py 文件是否存在且格式正确")
        return None, None, None


def check_configuration(config):
    """检查配置设置"""
    print("检查配置设置...")

    print(f"  服务器IP: {config['SERVER_IP']}")
    print(f"  客户端端口: {config['CLIENT_PORTS']}")
    print(f"  接口: {config['INTERFACE']}")
    print(f"  包长过滤: {config['PACKET_LENGTHS']}")
    print(f"  启用端口过滤: {config['ENABLE_PORT_FILTER']}")

    # 检查必要的配置
    issues = []
    if not config["SERVER_IP"] or config["SERVER_IP"] == "YOUR_SERVER_IP":
        issues.append("❌ 服务器IP未正确设置")
    if not config["INTERFACE"] or config["INTERFACE"] == "YOUR_INTERFACE":
        issues.append("❌ 网络接口未正确设置")

    if config["CLIENT_PORTS"] == []:
        print("⚠️  客户端端口列表为空，将捕获所有端口的数据包")
    if config["PACKET_LENGTHS"] == [None]:
        print("⚠️  包长过滤设置为[None]，这可能不是预期的过滤条件")

    if issues:
        for issue in issues:
            print(issue)
        return False

    print("✅ 配置检查通过")
    return True


def check_interface(config):
    """检查网络接口"""
    print("\n检查网络接口...")

    try:
        from scapy.all import get_if_list

        interfaces = get_if_list()
        print(f"系统可用接口: {interfaces}")

        if config["INTERFACE"] in interfaces:
            print(f"✅ 接口 '{config['INTERFACE']}' 可用")
            return True
        else:
            print(f"❌ 接口 '{config['INTERFACE']}' 不可用")
            print("请检查 config/settings.py 中的 INTERFACE 设置")
            return False

    except Exception as e:
        print(f"⚠️  检查接口时出错: {e}")
        print("继续测试...")
        return True


def test_capture_directly(process_packet, packet_queue, config):
    """直接测试捕获功能"""
    print("\n直接测试捕获功能...")

    try:
        from scapy.all import IP, TCP, Ether, Raw  # type: ignore

        # 创建一个测试数据包
        test_packet = (
            Ether()
            / IP(dst=config["SERVER_IP"], src="192.168.1.100")
            / TCP(dport=8080, sport=54321)
            / Raw(load=b"test data")
        )

        # 直接调用处理函数
        print("调用 process_packet 函数...")
        process_packet(test_packet)
        print("✅ process_packet 函数执行成功")

        # 检查队列中是否有数据
        try:
            record = packet_queue.get(timeout=0.1)
            print("✅ 数据包成功放入队列")
            print(f"   队列内容: {record[:50]}...")
            return True
        except Exception:  # type: ignore
            print("⚠️  数据包未放入队列（可能是过滤条件不匹配）")
            return False

    except Exception as e:
        print(f"❌ process_packet 函数执行失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def send_test_packets(config):
    """发送测试数据包"""
    print("\n开始发送测试数据包...")

    try:
        from scapy.all import IP, TCP, Ether, Raw, send  # type: ignore

        test_ip = config["SERVER_IP"]

        # 使用常用端口进行测试
        if config["CLIENT_PORTS"]:
            test_ports = config["CLIENT_PORTS"][:2]  # 只测试前两个端口
        else:
            test_ports = [8080, 8888]  # 默认测试端口

        test_data = "68656c6c6f20776f726c64"  # "hello world" 的hex

        sent_count = 0

        for port in test_ports:
            try:
                # 构造测试数据包
                packet = (
                    Ether()
                    / IP(dst=test_ip)
                    / TCP(dport=port)
                    / Raw(load=bytes.fromhex(test_data))
                )
                packet[TCP].sport = 50000 + sent_count

                send(packet, iface=config["INTERFACE"], verbose=0)
                print(f"✅ 发送测试包到 {test_ip}:{port}")
                sent_count += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ 发送测试包到 {test_ip}:{port} 失败: {e}")

        return sent_count

    except ImportError:
        print("❌ 无法导入scapy，跳过发送测试包")
        return 0


def monitor_queue(packet_queue, timeout=15):
    """监控队列并显示捕获的数据包"""
    print(f"\n开始监控队列，超时时间: {timeout}秒")
    start_time = time.time()
    packets_received = 0

    while time.time() - start_time < timeout:
        try:
            # 非阻塞获取队列数据
            record = packet_queue.get(timeout=1)
            packets_received += 1
            print(f"\n🎯 捕获到数据包 #{packets_received}:")
            print(f"  {record}")

        except Exception:
            # 超时是正常的，继续等待
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                print(f"⏳ 等待数据包... ({int(elapsed)}/{timeout}秒)")
            continue

    return packets_received


def main():
    """主测试函数"""
    print("=" * 60)
    print("🐛 捕获程序检查工具 (健壮版)")
    print("=" * 60)

    # 1. 导入配置
    config = safe_import_config()
    if config is None:
        return

    # 2. 导入捕获模块
    packet_queue, start_sniff, process_packet = safe_import_capture()
    if packet_queue is None:
        return

    # 3. 检查配置
    if not check_configuration(config):
        print("\n⚠️  请先修复配置问题")
        return

    # 4. 检查网络接口
    if not check_interface(config):
        return

    # 5. 直接测试捕获功能
    test_capture_directly(process_packet, packet_queue, config)

    # 6. 启动捕获线程
    print("\n启动捕获线程...")
    capture_thread = threading.Thread(target=start_sniff, daemon=True)
    capture_thread.start()

    # 等待捕获线程启动
    time.sleep(3)

    # 7. 发送测试数据包
    sent_count = send_test_packets(config)

    if sent_count == 0:
        print("❌ 未能发送任何测试包，请检查网络连接和权限")
        print("💡 提示: 可能需要使用 sudo 运行")
        return

    # 8. 监控队列
    print("\n等待捕获数据包...")
    packets_count = monitor_queue(packet_queue, timeout=20)

    # 9. 显示测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print("=" * 60)

    if packets_count > 0:
        print(f"✅ 成功捕获 {packets_count} 个数据包")
        print("🎉 捕获程序运行正常！")
    else:
        print("❌ 未捕获到任何数据包")
        print("\n🔍 可能的原因:")
        print("  - 权限不足 (尝试: sudo python check_capture_robust.py)")
        print("  - 网络接口配置错误")
        print("  - 过滤条件太严格")
        print("  - 数据包未到达目标服务器")
        print("  - 防火墙或安全软件阻止")

    print("\n检查完成。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 检查被用户中断。")
    except Exception as e:
        print(f"💥 检查过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
