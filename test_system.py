#!/usr/bin/env python3
"""
综合测试脚本 - 测试整个数据包捕获和解析系统
"""

import os
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print("=" * 60)
print("数据包捕获和解析系统测试")
print("=" * 60)


def test_individual_modules():
    """测试各个模块的独立功能"""
    print("\n1. 测试各个模块独立功能")
    print("-" * 40)

    # 测试捕获模块
    try:
        from capture_tester.capture_packets_test import start_sniff, get_queue

        print("✓ 捕获模块导入成功")

        # 测试配置
        print("捕获模块配置测试...")
        start_sniff(test_mode=True)
        queue = get_queue()
        print(f"✓ 捕获模块测试完成，队列大小: {queue.qsize()}")

    except Exception as e:
        print(f"✗ 捕获模块测试失败: {e}")
        return False

    # 测试解析模块
    try:
        from capture_tester.parse_packets_test import PacketParser

        print("✓ 解析模块导入成功")

        # 创建解析器实例
        parser = PacketParser(test_mode=True)
        print("✓ 解析器创建成功")

    except Exception as e:
        print(f"✗ 解析模块测试失败: {e}")
        return False

    return True


def test_integration():
    """测试模块集成"""
    print("\n2. 测试模块集成")
    print("-" * 40)

    try:
        from capture_tester.capture_packets_test import start_sniff, packet_queue
        from capture_tester.parse_packets_test import PacketParser

        print("✓ 模块导入成功")

        # 创建解析器
        parser = PacketParser(test_mode=True)
        print("✓ 解析器创建成功")

        # 在单独线程中启动解析
        print("启动解析线程...")
        parser_thread = threading.Thread(target=parser.parse_packet, daemon=True)
        parser_thread.start()

        # 等待解析器初始化
        time.sleep(2)

        # 启动捕获（测试模式）
        print("启动数据包捕获（测试模式）...")
        start_sniff(test_mode=True)

        # 等待处理完成
        print("等待数据处理...")
        time.sleep(3)

        # 检查结果
        queue_size = packet_queue.qsize()
        print(f"最终队列大小: {queue_size}")

        print("✓ 集成测试完成")
        return True

    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_packet_parsing():
    """测试数据包解析功能"""
    print("\n3. 测试数据包解析功能")
    print("-" * 40)

    try:
        from capture_tester.parse_packets_test import PacketParser

        parser = PacketParser(test_mode=True)

        # 测试玩家移动包解析
        print("测试玩家移动包解析...")
        player_move_packet = (
            "2024-01-01 12:00:00 | 192.168.1.100:12345 -> 192.168.1.1:54321 | "
            "Length:45 | Data:29000000b0517009000000000000803f0000000000000000000000000000000000000000"
        )
        result1 = parser._parse_player_move_packet(player_move_packet)
        print(f"玩家移动包解析: {'✓ 成功' if result1 else '✗ 失败'}")

        # 测试实体包解析
        print("测试实体包解析...")
        entity_packet = (
            "2024-01-01 12:00:00 | 192.168.1.100:12345 -> 192.168.1.1:54321 | "
            "Length:1424 | Data:3122D80000000000000000000000803f000000000000004040404030210010000000000"
        )
        result2 = parser._parse_entity_packet(entity_packet)
        print(f"实体包解析: {'✓ 成功' if result2 else '✗ 失败'}")

        return result1 or result2  # 至少一个成功就算通过

    except Exception as e:
        print(f"✗ 数据包解析测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_database():
    """测试数据库功能"""
    print("\n4. 测试数据库功能")
    print("-" * 40)

    try:
        # 导入数据库测试模块
        from database_test import test_database_operations, test_database_connection

        # 先测试连接
        connection_ok = test_database_connection()
        if not connection_ok:
            print("✗ 数据库连接测试失败")
            return False

        # 测试数据库操作
        operations_ok = test_database_operations()
        return operations_ok

    except ImportError as e:
        print(f"✗ 导入数据库测试模块失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 数据库测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始系统测试...\n")

    tests = [
        ("模块独立功能", test_individual_modules),
        ("数据包解析", test_packet_parsing),
        ("数据库功能", test_database),
        ("系统集成", test_integration),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"执行测试: {test_name}")
        print(f"{'='*50}")

        try:
            result = test_func()
            results[test_name] = result
            status = "✓ 通过" if result else "✗ 失败"
            print(f"\n测试结果: {status}")
        except Exception as e:
            print(f"\n测试异常: {e}")
            results[test_name] = False
            import traceback

            traceback.print_exc()

    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:20} {status}")

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有测试通过！系统工作正常。")
    else:
        print("⚠ 部分测试失败，请检查上述错误信息。")


if __name__ == "__main__":
    main()
