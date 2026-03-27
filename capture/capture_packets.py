# capture/capture_packets.py

"""
数据包捕获模块

该模块负责监听网络接口，捕获符合条件的数据包，并通过队列传递捕获结果。
主要功能包括：
- 基于IP、端口和包长的数据包过滤
- 实时数据包解析和处理
- 线程安全的数据包队列传递
"""

import os
import queue
import sys
import time

from scapy.all import IP, TCP, Raw, sniff  # type: ignore

# scapy.all：用于网络包的捕获、解析和构造

from config.settings import (
    CLIENT_PORTS,
    ENABLE_PORT_FILTER,
    INTERFACE,
    ENABLE_LENGTHS_FILTER,
    PACKET_LENGTHS,
    SERVER_IP,
)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建全局队列用于线程间传递数据包
packet_queue = queue.Queue()


def should_process_packet(ip_layer, tcp_layer, payload_len: int) -> bool:
    """
    判断是否应该处理当前数据包

    Args:
        ip_layer: IP层数据
        tcp_layer: TCP层数据
        payload_len: 载荷长度

    Returns:
        bool: 是否处理该数据包
    """
    # 检查目标IP是否为服务器IP
    if ip_layer.dst != SERVER_IP and ip_layer.src != SERVER_IP:
        return False

    # 端口过滤检查
    if ENABLE_PORT_FILTER:
        if tcp_layer.dport not in CLIENT_PORTS and tcp_layer.sport not in CLIENT_PORTS:
            return False

    # 长度过滤检查
    if not ENABLE_LENGTHS_FILTER:
        return True

    # 启用长度过滤时的处理
    if not PACKET_LENGTHS:
        return True

    # 检查包长是否在指定列表中
    if payload_len in PACKET_LENGTHS:
        return True

    # 检查是否有其他有效的过滤条件
    valid_lengths = [pl for pl in PACKET_LENGTHS if isinstance(pl, int) and pl > 0]
    return bool(valid_lengths)


def format_packet_record(ip_layer, tcp_layer, raw_layer, payload_len: int) -> str:
    """
    格式化数据包信息为字符串记录

    Args:
        ip_layer: IP层数据
        tcp_layer: TCP层数据
        raw_layer: 原始载荷数据
        payload_len: 载荷长度

    Returns:
        str: 格式化的数据包记录
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst
    src_port = tcp_layer.sport
    dst_port = tcp_layer.dport
    data = raw_layer.load.hex() if raw_layer else ""

    return (
        f"{timestamp} | {src_ip}:{src_port} -> {dst_ip}:{dst_port} | "
        f"Length:{payload_len} | Data:{data}"
    )


def process_packet(pkt) -> None:
    """
    处理每个捕获的数据包

    对每个数据包进行解析和过滤，符合条件的包会被格式化后放入队列。

    Args:
        pkt: 捕获的原始数据包
    """
    # 检查数据包是否包含IP和TCP层
    if IP not in pkt or TCP not in pkt:
        return

    ip_layer = pkt[IP]
    tcp_layer = pkt[TCP]
    raw_layer = pkt[Raw] if Raw in pkt else None
    payload_len = len(tcp_layer.payload)

    # 判断是否应该处理该数据包
    if should_process_packet(ip_layer, tcp_layer, payload_len):
        # 格式化数据包信息
        record = format_packet_record(ip_layer, tcp_layer, raw_layer, payload_len)

        # 将数据包记录放入队列
        packet_queue.put(record)


def start_sniff() -> None:
    """
    开始抓包操作

    启动网络接口监听，捕获符合条件的数据包。
    使用全局队列 packet_queue 传递捕获的数据包记录。
    """
    # 构建过滤条件显示信息
    port_filter_info = (
        f"端口={CLIENT_PORTS if CLIENT_PORTS else '无'}"
        if ENABLE_PORT_FILTER
        else "无端口过滤"
    )
    length_filter_info = f"包长={PACKET_LENGTHS if PACKET_LENGTHS else '无'}"

    print(
        f"开始监听接口 {INTERFACE}，过滤条件：目标IP={SERVER_IP}, "
        f"{port_filter_info},{length_filter_info}"
    )

    # 开始抓包，store=0表示不存储原始数据包
    sniff(iface=INTERFACE, prn=process_packet, store=0)


def main() -> None:
    """主函数"""
    try:
        start_sniff()
    except KeyboardInterrupt:
        print("\n捕获被用户中断。")
    except Exception as e:
        print(f"捕获过程中发生错误: {e}")
    finally:
        print("抓包程序结束。")


if __name__ == "__main__":
    main()
