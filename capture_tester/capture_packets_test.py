# capture_tester/capture_packets_test.py

"""
数据包捕获模块 - 测试版本

该模块负责监听网络接口，捕获符合条件的数据包，并通过队列传递捕获结果。
测试版本添加了详细的调试输出。
"""

import os
import queue
import sys
import time

from scapy.all import IP, TCP, Raw, sniff  # type: ignore

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置 - 测试版本使用简化配置
try:
    from config.settings import (
        CLIENT_PORTS,
        ENABLE_PORT_FILTER,
        INTERFACE,
        ENABLE_LENGTHS_FILTER,
        PACKET_LENGTHS,
        SERVER_IP,
    )

    print("✓ 成功导入配置")
except ImportError as e:
    print(f"✗ 导入配置失败: {e}")
    # 使用默认配置
    CLIENT_PORTS = [12345, 54321]
    ENABLE_PORT_FILTER = False
    INTERFACE = "eth0"
    ENABLE_LENGTHS_FILTER = False
    PACKET_LENGTHS = [45, 1424]
    SERVER_IP = "192.168.1.1"
    print("✓ 使用默认配置")

# 创建全局队列用于线程间传递数据包
packet_queue = queue.Queue()
print(f"✓ 创建数据包队列: {packet_queue}")


def should_process_packet(ip_layer, tcp_layer, payload_len: int) -> bool:
    """
    判断是否应该处理当前数据包 - 测试版本
    """
    print(
        f"  [过滤检查] 载荷长度: {payload_len}, 目标IP: {ip_layer.dst}, 源IP: {ip_layer.src}"
    )

    # 检查目标IP是否为服务器IP
    if ip_layer.dst != SERVER_IP and ip_layer.src != SERVER_IP:
        print(
            f"  [过滤] IP不匹配: 目标={ip_layer.dst}, 源={ip_layer.src}, 期望={SERVER_IP}"
        )
        return False
    else:
        print(f"  [过滤] IP匹配: 目标={ip_layer.dst}, 源={ip_layer.src}")

    # 端口过滤检查
    if ENABLE_PORT_FILTER:
        if tcp_layer.dport not in CLIENT_PORTS and tcp_layer.sport not in CLIENT_PORTS:
            print(
                f"  [过滤] 端口不匹配: 目标端口={tcp_layer.dport}, 源端口={tcp_layer.sport}, 期望={CLIENT_PORTS}"
            )
            return False
        else:
            print(
                f"  [过滤] 端口匹配: 目标端口={tcp_layer.dport}, 源端口={tcp_layer.sport}"
            )
    else:
        print("  [过滤] 端口过滤已禁用")

    # 长度过滤检查
    if not ENABLE_LENGTHS_FILTER:
        print("  [过滤] 长度过滤已禁用 - 接受数据包")
        return True

    # 启用长度过滤时的处理
    if not PACKET_LENGTHS:
        print("  [过滤] 长度过滤列表为空 - 接受数据包")
        return True

    # 检查包长是否在指定列表中
    if payload_len in PACKET_LENGTHS:
        print(f"  [过滤] 长度匹配: {payload_len} in {PACKET_LENGTHS} - 接受数据包")
        return True

    # 检查是否有其他有效的过滤条件
    valid_lengths = [pl for pl in PACKET_LENGTHS if isinstance(pl, int) and pl > 0]
    result = bool(valid_lengths)
    print(
        f"  [过滤] 长度不匹配: {payload_len} not in {PACKET_LENGTHS}, 有效长度检查: {result}"
    )

    return result


def format_packet_record(ip_layer, tcp_layer, raw_layer, payload_len: int) -> str:
    """
    格式化数据包信息为字符串记录 - 测试版本
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst
    src_port = tcp_layer.sport
    dst_port = tcp_layer.dport
    data = raw_layer.load.hex() if raw_layer else ""

    # 限制数据长度用于显示
    data_display = data[:50] + "..." if len(data) > 50 else data

    record = (
        f"{timestamp} | {src_ip}:{src_port} -> {dst_ip}:{dst_port} | "
        f"Length:{payload_len} | Data:{data_display}"
    )

    print(f"  [格式化] 创建记录: {record}")
    return record


def process_packet(pkt) -> None:
    """
    处理每个捕获的数据包 - 测试版本
    """
    print("\n=== 处理新数据包 ===")
    print(f"  [原始包] 长度: {len(pkt)} 字节")

    # 检查数据包是否包含IP和TCP层
    if IP not in pkt:
        print("  [错误] 数据包不包含IP层")
        return
    if TCP not in pkt:
        print("  [错误] 数据包不包含TCP层")
        return

    ip_layer = pkt[IP]
    tcp_layer = pkt[TCP]
    raw_layer = pkt[Raw] if Raw in pkt else None
    payload_len = len(tcp_layer.payload)

    print(f"  [解析] IP: {ip_layer.src} -> {ip_layer.dst}")
    print(f"  [解析] 端口: {tcp_layer.sport} -> {tcp_layer.dport}")
    print(f"  [解析] 载荷长度: {payload_len}")
    print(f"  [解析] 原始层: {'有' if raw_layer else '无'}")

    # 判断是否应该处理该数据包
    if should_process_packet(ip_layer, tcp_layer, payload_len):
        # 格式化数据包信息
        record = format_packet_record(ip_layer, tcp_layer, raw_layer, payload_len)

        # 将数据包记录放入队列
        print(f"  [队列] 准备放入队列，当前队列大小: {packet_queue.qsize()}")
        packet_queue.put(record)
        print(f"  [队列] 成功放入，当前队列大小: {packet_queue.qsize()}")
    else:
        print("  [过滤] 数据包不符合处理条件，已丢弃")


def start_sniff(test_mode=False) -> None:
    """
    开始抓包操作 - 测试版本
    """
    print("\n" + "=" * 50)
    print("启动抓包系统")
    print("=" * 50)

    # 构建过滤条件显示信息
    port_filter_info = (
        f"端口={CLIENT_PORTS if CLIENT_PORTS else '无'}"
        if ENABLE_PORT_FILTER
        else "无端口过滤"
    )
    length_filter_info = f"包长={PACKET_LENGTHS if PACKET_LENGTHS else '无'}"

    print(f"接口: {INTERFACE}")
    print(f"目标IP: {SERVER_IP}")
    print(f"端口过滤: {port_filter_info}")
    print(f"长度过滤: {length_filter_info}")
    print(f"测试模式: {test_mode}")

    if test_mode:
        print("\n[测试模式] 模拟数据包捕获...")
        # 在测试模式下，模拟一些数据包
        test_packets = [
            # 模拟玩家移动包
            "2024-01-01 12:00:00 | 192.168.1.100:12345 -> 192.168.1.1:54321 | Length:45 | Data:29000000b0517009000000000000803f0000000000000000000000000000000000000000",
            # 模拟实体包
            "2024-01-01 12:00:00 | 192.168.1.100:12345 -> 192.168.1.1:54321 | Length:1424 | Data:3122D80000000000000000000000803f00000000000000000000404130210010000000000",
        ]

        for i, packet in enumerate(test_packets):
            print(f"\n[测试] 模拟数据包 {i+1}/{len(test_packets)}")
            packet_queue.put(packet)
            time.sleep(1)

        print("\n[测试] 所有测试数据包已放入队列")
        return

    print("\n开始真实数据包捕获...")
    try:
        # 开始抓包，store=0表示不存储原始数据包
        sniff(
            iface=INTERFACE, prn=process_packet, store=0, count=10
        )  # 只捕获10个包用于测试
    except Exception as e:
        print(f"抓包错误: {e}")
        print("请检查网络接口配置和权限")


def get_queue():
    """获取数据包队列"""
    return packet_queue


def main() -> None:
    """主函数 - 测试版本"""
    print("数据包捕获模块测试版")
    try:
        start_sniff(test_mode=True)  # 使用测试模式
    except KeyboardInterrupt:
        print("\n捕获被用户中断。")
    except Exception as e:
        print(f"捕获过程中发生错误: {e}")
    finally:
        print(f"最终队列大小: {packet_queue.qsize()}")
        print("抓包程序结束。")


if __name__ == "__main__":
    main()
