# capture_tester/parse_packets_test.py

"""
数据包解析模块 - 测试版本

该模块负责解析从网络捕获的数据包，提取游戏实体信息和玩家移动数据。
测试版本添加了详细的调试输出和数据库测试功能。
"""

import time
import json
import logging
import queue
import re
import struct
import threading
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logger = logging.getLogger()

# 设置日志级别
logger.setLevel(logging.DEBUG)  # 测试版本使用DEBUG级别

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 设置日志格式
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(console_handler)

print("✓ 日志系统初始化完成")

# 导入其他模块
try:
    from capture_tester.capture_packets_test import packet_queue

    print("✓ 成功导入 packet_queue")
except ImportError as e:
    print(f"✗ 导入 packet_queue 失败: {e}")
    # 创建模拟队列
    packet_queue = queue.Queue()
    print("✓ 创建模拟队列")

try:
    from database.operations import DatabaseOperations

    print("✓ 成功导入 DatabaseOperations")
except ImportError as e:
    print(f"✗ 导入 DatabaseOperations 失败: {e}")
    DatabaseOperations = None


class PacketParser:
    """
    数据包解析器 - 测试版本
    """

    # 数据包类型常量
    PLAYER_MOVE_PACKET_LENGTH = 45
    ENTITY_PACKET_LENGTHS = [1424]

    # 数据包特征码
    PLAYER_MOVE_OPCODE = 0x097051B0

    def __init__(self, test_mode=False):
        """
        初始化数据包解析器 - 测试版本
        """
        print("\n" + "=" * 50)
        print("初始化数据包解析器")
        print("=" * 50)

        self.test_mode = test_mode

        # 检查当前工作目录和配置文件
        print(f"当前工作目录: {os.getcwd()}")
        print(f"脚本目录: {os.path.dirname(os.path.abspath(__file__))}")

        # 加载 ID 映射文件
        print("\n加载ID映射文件...")
        self.plant_mapping = self._load_id_mapping("config/plant_id_mapping.json")
        self.ore_mapping = self._load_id_mapping("config/ore_id_mapping.json")

        print(f"植物映射: {len(self.plant_mapping)} 项")
        print(f"矿物映射: {len(self.ore_mapping)} 项")

        if self.plant_mapping:
            print(f"植物映射示例: {list(self.plant_mapping.items())[:3]}")
        if self.ore_mapping:
            print(f"矿物映射示例: {list(self.ore_mapping.items())[:3]}")

        # 初始化数据库操作实例
        print("\n初始化数据库连接...")
        self.db_ops = self._initialize_database()

        # 接收传递过来的队列
        self.packet_queue = packet_queue
        print(f"数据包队列: {self.packet_queue}")

    def _initialize_database(self):
        """初始化数据库连接 - 适配实际DatabaseOperations类"""
        if DatabaseOperations is None:
            print("✗ DatabaseOperations 不可用，使用模拟数据库")
            return self._create_mock_database()

        try:
            db_ops = DatabaseOperations()
            print("✓ 数据库操作实例创建成功")

            # 通过简单的插入操作测试连接
            test_success = db_ops.insert_player_move(
                position_x=0.0, position_y=0.0, packet_source="parser_init_test"
            )

            if test_success:
                print("✓ 数据库连接测试成功")
            else:
                print("✗ 数据库连接测试失败")

            return db_ops

        except Exception as e:
            print(f"✗ 数据库初始化失败: {e}")
            return self._create_mock_database()

    def _create_mock_database(self):
        """创建模拟数据库用于测试 - 适配实际接口"""
        print("创建模拟数据库操作类...")

        class MockDB:
            def __init__(self):
                self.operations_log = []
                print("✓ 模拟数据库已创建")

            def insert_player_move(
                self, position_x, position_y, packet_source=None, **kwargs
            ):
                self.operations_log.append(
                    {
                        "type": "player_move",
                        "position_x": position_x,
                        "position_y": position_y,
                        "source": packet_source,
                    }
                )
                print(f"✓ 模拟插入玩家移动: X={position_x:.2f}, Y={position_y:.2f}")
                return True

            def insert_camera_move(
                self, angle_x, angle_y, packet_source=None, **kwargs
            ):
                self.operations_log.append(
                    {
                        "type": "camera_move",
                        "angle_x": angle_x,
                        "angle_y": angle_y,
                        "source": packet_source,
                    }
                )
                print(f"✓ 模拟插入视角移动: X角度={angle_x:.4f}, Y角度={angle_y:.4f}")
                return True

            def insert_entity_data(self, entity_data):
                self.operations_log.append({"type": "entity", "data": entity_data})
                print(
                    f"✓ 模拟插入实体: {entity_data['entity_name']}(ID:{entity_data['entity_id']})"
                )
                return True

            def record_unknown_entity(
                self, entity_id, position_x=None, position_y=None, raw_hex_data=None
            ):
                self.operations_log.append(
                    {
                        "type": "unknown_entity",
                        "entity_id": entity_id,
                        "position_x": position_x,
                        "position_y": position_y,
                    }
                )
                print(f"✓ 模拟记录未知实体: ID={entity_id}")
                return True

            def log_system_event(self, level, message, module=None):
                self.operations_log.append(
                    {
                        "type": "system_log",
                        "level": level,
                        "message": message,
                        "module": module,
                    }
                )
                print(f"✓ 模拟系统日志: [{level}] {message}")
                return True

            def get_operations_log(self):
                return self.operations_log

            def clear_operations_log(self):
                self.operations_log.clear()
                print("✓ 模拟数据库操作日志已清空")

        return MockDB()

    def _load_id_mapping(self, config_path: str) -> dict:
        """
        加载ID映射配置文件 - 测试版本
        """
        print(f"尝试加载映射文件: {config_path}")

        # 尝试多个可能的路径
        possible_paths = [
            config_path,
            f"../{config_path}",
            f"../../{config_path}",
            os.path.join(os.path.dirname(__file__), config_path),
            os.path.join(os.path.dirname(__file__), f"../{config_path}"),
        ]

        for path in possible_paths:
            full_path = Path(path)
            print(f"  检查路径: {full_path} (存在: {full_path.exists()})")
            if full_path.exists():
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        mapping = json.load(f)
                    print(f"✓ 成功加载映射文件: {path}")
                    return mapping
                except Exception as e:
                    print(f"✗ 加载映射文件失败 {path}: {e}")

        print("⚠ 所有路径尝试失败，使用空映射")
        # 返回一些测试数据
        return {
            "001": "测试植物1",
            "002": "测试植物2",
            "001001": "测试矿物1",
            "001002": "测试矿物2",
        }

    def parse_packet(self):
        """
        主解析循环 - 测试版本
        """
        print("\n" + "=" * 50)
        print("开始解析数据包")
        print("=" * 50)

        # 等待抓包系统初始化完成
        print("解析器等待抓包系统就绪...")
        time.sleep(2)

        print(f"初始队列大小: {self.packet_queue.qsize()}")
        packet_count = 0

        # 如果是测试模式，设置超时避免永久等待
        timeout = 10 if self.test_mode else 1

        while True:
            try:
                print(f"\n等待数据包... (队列大小: {self.packet_queue.qsize()})")

                # 从队列中获取数据包
                packet = self.packet_queue.get(timeout=timeout)
                packet_count += 1

                print(f"\n=== 处理数据包 #{packet_count} ===")
                print(f"数据包内容: {packet[:100]}...")

                if packet is None:
                    print("收到停止信号，退出解析循环")
                    break

                # 尝试按类型解析数据包
                parsed_as_player = self._parse_player_move_packet(packet)
                parsed_as_entity = self._parse_entity_packet(packet)

                print(f"解析结果: 玩家移动={parsed_as_player}, 实体={parsed_as_entity}")

                if not parsed_as_player and not parsed_as_entity:
                    print("⚠ 数据包未被任何解析器识别")
                    # 显示数据包详细信息用于调试
                    payload_length, data_hex = self._extract_packet_data_hex(packet)
                    print(f"  载荷长度: {payload_length}")
                    print(f"  数据长度: {len(data_hex) if data_hex else 0}")
                    if data_hex:
                        print(f"  数据前100字符: {data_hex[:100]}")

                # 标记任务完成
                self.packet_queue.task_done()
                print("数据包处理完成")

                # 测试模式下处理一定数量后退出
                if self.test_mode and packet_count >= 5:
                    print(f"测试模式: 已处理 {packet_count} 个数据包，退出循环")
                    break

            except queue.Empty:
                print(f"队列为空，等待数据包... (已处理: {packet_count})")
                if self.test_mode and packet_count == 0:
                    # 测试模式下如果没有数据包，模拟一些测试数据
                    print("测试模式: 模拟测试数据包")
                    self._inject_test_packets()
                    continue
                elif self.test_mode:
                    break
                continue
            except KeyboardInterrupt:
                print("解析器收到中断信号，停止解析")
                break
            except Exception as e:
                print(f"❌ 解析数据包时发生错误: {e}")
                import traceback

                traceback.print_exc()
                if not self.packet_queue.empty():
                    self.packet_queue.task_done()

        print(f"\n解析循环结束，共处理 {packet_count} 个数据包")

        # 显示数据库操作结果
        if hasattr(self.db_ops, "get_insertions"):
            insertions = self.db_ops.get_insertions()
            print("\n数据库操作统计:")
            print(f"  总操作数: {len(insertions)}")
            types = {}
            for ins in insertions:
                t = ins["type"]
                types[t] = types.get(t, 0) + 1
            for t, count in types.items():
                print(f"  {t}: {count}")

    def _inject_test_packets(self):
        """注入测试数据包"""
        test_packets = [
            # 玩家移动包
            "2024-01-01 12:00:00 | 192.168.1.100:12345 -> 192.168.1.1:54321 | Length:45 | Data:29000000b0517009000000000000803f0000000000000000000000000000000000000000",
            # 实体包
            "2024-01-01 12:00:00 | 192.168.1.100:12345 -> 192.168.1.1:54321 | Length:1424 | Data:3122D80000000000000000000000803f000000000000004040404030210010000000000",
        ]

        for i, packet in enumerate(test_packets):
            print(f"注入测试数据包 {i+1}/{len(test_packets)}")
            self.packet_queue.put(packet)

    def _extract_packet_data_hex(self, packet: str) -> tuple:
        """
        从数据包字符串中提取载荷长度和十六进制数据 - 测试版本
        """
        print("  提取数据包数据...")

        parts = packet.split(" | ")
        payload_length = None
        data_hex = None

        for part in parts:
            if part.startswith("Length:"):
                payload_length = int(part.split(":")[1])
                print(f"    载荷长度: {payload_length}")
            elif part.startswith("Data:"):
                data_hex = part[5:].replace(" ", "").upper()
                print(f"    数据长度: {len(data_hex)} 字符")

        return payload_length, data_hex

    def _parse_player_move_packet(self, packet: str) -> bool:
        """
        解析玩家移动数据包 - 测试版本
        """
        print("  尝试解析为玩家移动包...")

        payload_length, data_hex = self._extract_packet_data_hex(packet)
        if not payload_length or not data_hex:
            print("    缺少必要数据")
            return False

        # 检查是否为玩家移动数据包
        if payload_length != self.PLAYER_MOVE_PACKET_LENGTH:
            print(
                f"    长度不匹配: {payload_length} != {self.PLAYER_MOVE_PACKET_LENGTH}"
            )
            return False

        if len(data_hex) < 90:
            print(f"    数据太短: {len(data_hex)} < 90")
            return False

        print("    基本检查通过，开始解析字段...")

        try:
            # 解析数据包各字段
            pkt_length = struct.unpack("<I", bytes.fromhex(data_hex[0:8]))[0]
            print(f"    数据包长度字段: {pkt_length} (0x{pkt_length:08X})")

            if pkt_length != 0x29:  # 应该是45
                print(f"    长度字段不匹配: 0x{pkt_length:08X} != 0x29")
                return False

            opcode = struct.unpack("<I", bytes.fromhex(data_hex[8:16]))[0]
            print(f"    操作码: 0x{opcode:08X}")

            if opcode != self.PLAYER_MOVE_OPCODE:
                print(
                    f"    操作码不匹配: 0x{opcode:08X} != 0x{self.PLAYER_MOVE_OPCODE:08X}"
                )
                return False

            # 提取坐标
            x = struct.unpack("<f", bytes.fromhex(data_hex[24:32]))[0]
            y = struct.unpack("<f", bytes.fromhex(data_hex[40:48]))[0]

            print(f"    解析成功: X={x:.2f}, Y={y:.2f}")

            # 插入数据库
            success = self.db_ops.insert_player_move(
                position_x=x, position_y=y, packet_source="packet_parser_test"
            )

            if success:
                print("    ✓ 玩家移动数据已保存")
            else:
                print("    ✗ 玩家移动数据保存失败")

            return True

        except (ValueError, IndexError, struct.error) as e:
            print(f"    ✗ 解析玩家移动数据包失败: {e}")
            return False

    def _parse_entity_packet(self, packet: str):
        """解析实体数据包 - 测试版本"""
        print("  尝试解析为实体包...")

        payload_length, data_hex = self._extract_packet_data_hex(packet)
        if not payload_length or not data_hex:
            return False

        # 检查是否为实体数据包
        if payload_length not in self.ENTITY_PACKET_LENGTHS:
            print(
                f"    长度不匹配: {payload_length} not in {self.ENTITY_PACKET_LENGTHS}"
            )
            return False

        print("    长度匹配，开始提取实体数据...")

        # 提取实体数据
        entities_data = self._extract_entity_data(data_hex)
        if not entities_data:
            print("    未提取到实体数据")
            return False

        print(f"    提取到 {len(entities_data)} 个实体")

        # 处理每个实体
        success_count = 0
        for i, entity_data in enumerate(entities_data):
            x, y, index = entity_data
            print(f"      实体 #{i+1}: ID={index}, X={x:.2f}, Y={y:.2f}")

            entity_info = self._generate_entity_info(index)
            print(f"        实体信息: {entity_info}")

            # 记录未知ID用于后续分析
            if entity_info["is_unknown"]:
                print(f"        ⚠ 未知实体ID: {index}")
            else:
                print(f"        ✓ 已知实体: {entity_info['name']}")

            # 准备插入实体数据表的字典
            entity_data_dict = {
                "entity_id": index,
                "entity_type": entity_info["type"],
                "entity_name": entity_info["name"],
                "category": entity_info.get("category"),
                "growth_stage": entity_info.get("growth_stage"),
                "maturity_level": entity_info.get("maturity_level", 0),
                "is_mature": entity_info.get("is_mature", False),
                "position_x": x,
                "position_y": y,
                "is_unknown": entity_info["is_unknown"],
                "raw_data": None,
            }

            # 插入到实体数据表
            if self.db_ops.insert_entity_data(entity_data_dict):
                print("        ✓ 实体数据插入成功")
            else:
                print("        ✗ 实体数据插入失败")

            # 如果是未知实体，额外记录到未知实体表
            if entity_info["is_unknown"]:
                if self.db_ops.record_unknown_entity(
                    entity_id=index,
                    position_x=x,
                    position_y=y,
                    raw_hex_data=hex(index),
                ):
                    print("        ✓ 未知实体记录成功")
                else:
                    print("        ✗ 未知实体记录失败")

            success_count += 1

        print(f"    ✓ 成功处理 {success_count} 个实体")
        return success_count > 0

    def _extract_entity_data(self, data_hex: str) -> list:
        """从十六进制数据中提取实体信息 - 测试版本"""
        print("    提取实体数据...")

        try:
            # 匹配实体数据模式
            pattern = re.compile(
                r"3122D800"  # 起始标志
                r"[0-9A-F]{8}"  # 跳过
                r"([0-9A-F]{8})"  # 跳过match[0]
                r"([0-9A-F]{8})"  # 跳过
                r"([0-9A-F]{8})"  # X坐标
                r"([0-9A-F]{8})"  # 跳过
                r"([0-9A-F]{8})"  # Y坐标
                r"([0-9A-F]{8})"  # 跳过
                r"([0-9A-F]{8})"  # 跳过
                r"([0-9A-F]{8})"  # 实体索引
            )

            matches = pattern.findall(data_hex)
            print(f"    找到 {len(matches)} 个匹配模式")

            if not matches:
                return []

            entities = []
            for i, match in enumerate(matches):
                print(f"      处理匹配 #{i+1}")

                # 字段映射
                x_hex, y_hex, index_hex = match[2], match[4], match[7]
                print(f"        X十六进制: {x_hex}")
                print(f"        Y十六进制: {y_hex}")
                print(f"        索引十六进制: {index_hex}")

                try:
                    x = struct.unpack("<f", bytes.fromhex(x_hex))[0]
                    y = struct.unpack("<f", bytes.fromhex(y_hex))[0]

                    # 索引处理
                    index = int(bytes.fromhex(index_hex)[::-1].hex(), 16)

                    print(f"        解析: X={x:.2f}, Y={y:.2f}, ID={index}")
                    entities.append((x, y, index))

                except (ValueError, struct.error) as e:
                    print(f"        解析实体字段失败: {e}")
                    continue

            return entities
        except Exception as e:
            print(f"    ✗ 提取实体数据时出错: {e}")
            return []

    def _generate_entity_info(self, index: int) -> dict:
        """根据实体ID生成实体信息 - 测试版本"""
        print(f"      生成实体信息: ID={index}")

        index_str = str(index)
        print(f"        实体ID字符串: '{index_str}'")

        # 植物类 (302开头)
        if index_str.startswith("302") and len(index_str) == 7:
            print("        识别为植物类")
            category = index_str[3:6]  # 中间三位表示种类
            growth_stage = index_str[6]  # 最后一位表示生长状态
            maturity_level = int(index_str[3]) + 1  # 第一位表示阶数-1

            # 从配置文件中获取植物名称
            plant_name = self.plant_mapping.get(category, f"未知植物({category})")
            print(
                f"        植物信息: 种类={category}, 生长阶段={growth_stage}, 阶数={maturity_level}, 名称={plant_name}"
            )

            # 植物成熟条件：生长阶段为5
            is_mature = int(growth_stage) == 5

            return {
                "index": index,
                "type": "plant",
                "category": category,
                "name": plant_name,
                "growth_stage": int(growth_stage),
                "maturity_level": maturity_level,
                "is_mature": is_mature,
                "is_unknown": plant_name.startswith("未知植物"),
            }

        # 矿物类 (301开头)
        elif index_str.startswith("301") and len(index_str) == 7:
            print("        识别为矿物类")
            mineral_type = index_str[3:]  # 后四位表示矿物种类
            maturity_level = int(index_str[3])  # 第一位表示阶数

            # 从配置文件中获取矿物名称
            mineral_name = self.ore_mapping.get(
                mineral_type, f"未知矿物({mineral_type})"
            )
            print(
                f"        矿物信息: 种类={mineral_type}, 阶数={maturity_level}, 名称={mineral_name}"
            )

            # 矿物没有生长阶段，采集到就是成熟的
            is_mature = True

            return {
                "index": index,
                "type": "ore",
                "category": mineral_type,
                "name": mineral_name,
                "maturity_level": maturity_level,
                "is_mature": is_mature,
                "is_unknown": mineral_name.startswith("未知矿物"),
            }
        else:
            print(f"        未知实体类型: {index_str}")
            return {
                "index": index,
                "type": "unknown",
                "category": "unknown",
                "name": f"Unknown({index})",
                "is_unknown": True,
                "maturity_level": 0,
                "is_mature": False,
            }


def main():
    """主函数 - 测试版本"""
    print("数据包解析模块测试版")

    # 创建解析器实例
    parser = PacketParser(test_mode=True)

    # 启动解析程序
    parser_thread = threading.Thread(target=parser.parse_packet, daemon=True)
    parser_thread.start()

    try:
        parser_thread.join()
    except KeyboardInterrupt:
        print("解析中止。")
    finally:
        print("解析程序结束。")


if __name__ == "__main__":
    main()
