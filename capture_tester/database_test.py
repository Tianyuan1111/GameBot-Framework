#!/usr/bin/env python3
"""
数据库操作测试模块
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print("=" * 50)
print("数据库操作测试")
print("=" * 50)


def test_database_operations():
    """测试数据库操作类的基本功能"""

    try:
        from database.operations import DatabaseOperations

        print("✓ 成功导入 DatabaseOperations")
    except ImportError as e:
        print(f"✗ 导入 DatabaseOperations 失败: {e}")
        return False

    try:
        # 创建数据库操作实例
        db_ops = DatabaseOperations()
        print("✓ 数据库操作实例创建成功")
    except Exception as e:
        print(f"✗ 数据库操作实例创建失败: {e}")
        return False

    test_results = {}

    # 测试1: 插入玩家移动数据
    print("\n1. 测试插入玩家移动数据...")
    try:
        success = db_ops.insert_player_move(
            position_x=100.5, position_y=200.3, packet_source="database_test"
        )
        test_results["玩家移动插入"] = success
        print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")
    except Exception as e:
        test_results["玩家移动插入"] = False
        print(f"  结果: ✗ 异常 - {e}")

    # 测试2: 插入视角移动数据
    print("\n2. 测试插入视角移动数据...")
    try:
        success = db_ops.insert_camera_move(
            angle_x=45.5, angle_y=30.2, packet_source="database_test"
        )
        test_results["视角移动插入"] = success
        print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")
    except Exception as e:
        test_results["视角移动插入"] = False
        print(f"  结果: ✗ 异常 - {e}")

    # 测试3: 插入实体数据
    print("\n3. 测试插入实体数据...")
    try:
        entity_data = {
            "entity_id": 3021001,
            "entity_type": "plant",
            "entity_name": "测试植物",
            "category": "001",
            "growth_stage": 3,
            "maturity_level": 1,
            "is_mature": False,
            "position_x": 150.7,
            "position_y": 250.9,
            "is_unknown": False,
            "raw_data": None,
        }
        success = db_ops.insert_entity_data(entity_data)
        test_results["实体数据插入"] = success
        print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")
    except Exception as e:
        test_results["实体数据插入"] = False
        print(f"  结果: ✗ 异常 - {e}")

    # 测试4: 记录未知实体
    print("\n4. 测试记录未知实体...")
    try:
        success = db_ops.record_unknown_entity(
            entity_id=999999,
            position_x=300.1,
            position_y=400.2,
            raw_hex_data="0x123456",
        )
        test_results["未知实体记录"] = success
        print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")
    except Exception as e:
        test_results["未知实体记录"] = False
        print(f"  结果: ✗ 异常 - {e}")

    # 测试5: 记录系统事件
    print("\n5. 测试记录系统事件...")
    try:
        success = db_ops.log_system_event(
            level="INFO", message="数据库测试完成", module="test_database"
        )
        test_results["系统事件记录"] = success
        print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")
    except Exception as e:
        test_results["系统事件记录"] = False
        print(f"  结果: ✗ 异常 - {e}")

    # 输出测试总结
    print("\n" + "=" * 50)
    print("数据库测试总结")
    print("=" * 50)

    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:15} {status}")

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    return passed == total


def test_database_connection():
    """测试数据库连接"""
    print("\n测试数据库连接...")

    try:
        from database.operations import DatabaseOperations
        from database.config import db_config

        # 测试数据库配置
        print("数据库配置信息:")
        print(f"  数据库URL: {db_config.database_url}")
        print(f"  连接池大小: {db_config.pool_size}")

        # 创建操作实例测试连接
        db_ops = DatabaseOperations()
        print("✓ 数据库连接成功")

        # 通过简单的插入操作测试连接
        test_success = db_ops.insert_player_move(
            position_x=0.0, position_y=0.0, packet_source="connection_test"
        )

        if test_success:
            print("✓ 数据库操作测试成功")
            return True
        else:
            print("✗ 数据库操作测试失败")
            return False

    except Exception as e:
        print(f"✗ 数据库连接测试失败: {e}")
        return False


if __name__ == "__main__":
    # 运行连接测试
    connection_ok = test_database_connection()

    if connection_ok:
        print("\n" + "=" * 50)
        print("开始详细数据库操作测试")
        print("=" * 50)
        test_database_operations()
    else:
        print("\n数据库连接失败，跳过详细操作测试")
