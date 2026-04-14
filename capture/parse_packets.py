# capture/parse_packets.py

"""
数据包解析模块

该模块负责解析从网络捕获的数据包，提取游戏实体信息和玩家移动数据。
主要功能包括：
- 解析玩家移动数据包，提取坐标信息
- 解析实体数据包（植物、矿物等），提取类型和位置信息
- 基于ID映射配置识别实体种类和属性
- 将解析结果保存到数据库和日志文件
- 支持多线程实时解析数据包队列

数据包类型支持：
- 玩家移动数据包（45字节）
- 实体数据包（1424字节）
- 视角移动数据包（10字节）

依赖配置：
- plant_id_mapping.json：植物ID映射配置
- ore_id_mapping.json：矿物ID映射配置
"""
import time
import json
import logging
import queue
import re
import struct
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 导入其他模块
from capture.capture_packets import packet_queue
from database.operations import DatabaseOperations

# 配置日志
logger = logging.getLogger()

# 设置日志级别
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建文件处理器（带有文件大小限制）
file_handler = RotatingFileHandler(
    "app.log", maxBytes=5 * 1024 * 1024, backupCount=3
)  # 最大 5MB, 最多 3 个备份文件
file_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter("%(asctime)s - %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class PacketParser:
    """
    数据包解析器，负责解析网络数据包并提取游戏实体信息

    主要功能：
    - 解析玩家移动数据包
    - 解析实体数据包（植物、矿物等）
    - 将解析结果保存到数据库和文件
    """

    # 数据包类型常量
    PLAYER_MOVE_PACKET_LENGTH = 45  # 玩家移动数据包长度
    ENTITY_PACKET_LENGTHS = [1424]  # 实体数据包长度列表

    # 数据包特征码
    PLAYER_MOVE_OPCODE = 0x097051B0  # 玩家移动操作码

    def __init__(self):
        """
        初始化数据包解析器

        功能：
        - 加载ID映射配置文件
        - 初始化数据库操作实例
        - 获取数据包队列
        """

        # 初始化时，加载 ID 映射文件
        self.plant_mapping = self._load_id_mapping("config/plant_id_mapping.json")
        self.ore_mapping = self._load_id_mapping("config/ore_id_mapping.json")

        # 初始化时创建数据库操作实例
        self.db_ops = DatabaseOperations()

        # 接收传递过来的队列
        self.packet_queue = packet_queue

    def _load_id_mapping(self, config_path: str) -> dict:
        """
        加载ID映射配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            dict: 映射字典，如果加载失败返回空字典
        """
        path = Path(config_path)
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"映射配置文件不存在: {path}")
                return {}
        except Exception as e:
            logger.error(f"加载映射配置失败: {e}")
            return {}

    def parse_packet(self):
        """
        主解析循环：实时解析从队列中取出的数据包

        流程：
        1. 从队列获取数据包
        2. 尝试解析为玩家移动包
        3. 尝试解析为实体包
        4. 记录无法识别的数据包
        5. 标记任务完成
        """

        # 等待抓包系统初始化完成
        print("解析器等待抓包系统就绪...")
        time.sleep(3)
        print("开始解析数据包...")

        while True:
            try:
                # 从队列中获取数据包，设置超时避免永久阻塞
                packet = self.packet_queue.get(timeout=1)
                if packet is None:
                    break  # 如果队列为空或收到停止信号，则跳出循环

                # 尝试按类型解析数据包
                if self._parse_player_move_packet(packet):
                    # 解析成功，继续下一个
                    pass
                elif self._parse_entity_packet(packet):
                    # 解析成功，继续下一个
                    pass
                else:
                    # 无法识别的数据包类型
                    logger.debug("无法识别的数据包类型")

                # 无论是否解析成功，都标记任务完成
                self.packet_queue.task_done()

            except queue.Empty:
                # 队列为空，继续等待
                continue
            except KeyboardInterrupt:
                logger.info("解析器收到中断信号，停止解析")
                break
            except Exception as e:
                logger.error(f"解析数据包时发生错误: {e}")
                if not self.packet_queue.empty():
                    self.packet_queue.task_done()

    def _extract_packet_data_hex(self, packet: str) -> tuple:
        """
        从数据包字符串中提取载荷长度和十六进制数据

        Args:
            packet: 格式化的数据包字符串，格式为 "Length:xxx | Data:xxxx"

        Returns:
            tuple: (payload_length, data_hex) 或 (None, None)
        """
        parts = packet.split(" | ")
        payload_length = None
        data_hex = None

        for part in parts:
            if part.startswith("Length:"):
                payload_length = int(part.split(":")[1])
            elif part.startswith("Data:"):
                data_hex = part[5:].replace(" ", "").upper()  # 清理数据

        return payload_length, data_hex

    def _parse_player_move_packet(self, packet: str) -> bool:
        """
        解析玩家移动数据包

        Args:
            packet: 格式化的数据包字符串

        Returns:
            bool: 是否成功解析

        玩家移动包长度：PLAYER_MOVE_PACKET_LENGTH
        玩家移动操作码：PLAYER_MOVE_OPCODE
        """

        # 提取数据包基本信息
        payload_length, data_hex = self._extract_packet_data_hex(packet)
        if not payload_length or not data_hex:
            return False

        # 检查是否为玩家移动数据包
        if payload_length != self.PLAYER_MOVE_PACKET_LENGTH:
            return False
        if len(data_hex) < 90:  # 45字节 = 90个十六进制字符
            return False

        try:
            # 解析数据包各字段
            # 数据包结构:
            # 0-3: 数据包长度 (4字节)
            # 4-7: 操作码 (4字节)
            # 8-11: 未知字段 (4字节)
            # 12-15: X坐标 (4字节浮点数)
            # 16-19: 未知字段 (4字节)
            # 20-23: Y坐标 (4字节浮点数)
            # 剩余字段: 速度分量和其他未知字段
            pkt_length = struct.unpack("<I", bytes.fromhex(data_hex[0:8]))[0]
            if pkt_length != 0x29:  # 应该是45
                return False

            opcode = struct.unpack("<I", bytes.fromhex(data_hex[8:16]))[0]

            if opcode != 0x097051B0:  # 如果需要检查操作码
                return False

            # 12-15: 提取X坐标 (float32)
            x = struct.unpack("<f", bytes.fromhex(data_hex[24:32]))[0]

            # 20-23: 提取Y坐标 (float32)
            y = struct.unpack("<f", bytes.fromhex(data_hex[40:48]))[0]

            # 24-27: X方向速度分量（float32）
            # velocity_x = struct.unpack("<f", bytes.fromhex(data_part[48:56]))[0]

            # 28-31: Y方向速度分量（float32）
            # velocity_y = struct.unpack("<f", bytes.fromhex(data_part[56:64]))[0]

            # 记录玩家坐标数据到文件
            # self._write_to_file(
            #    "player_moves.txt", f"Player Move: X={x:.2f}, Y={y:.2f}"
            # )

            # 插入数据库
            success = self.db_ops.insert_player_move(
                position_x=x, position_y=y, packet_source="packet_parser"
            )

            if success:
                logger.debug("玩家移动数据已保存到数据库")
            else:
                logger.warning("玩家移动数据保存失败")
                # logger.debug(f"解析玩家移动: X={x:.2f}, Y={y:.2f}")

            return True

        except (ValueError, IndexError, struct.error) as e:
            logger.warning(f"解析玩家移动数据包失败: {e}")
            return False

    def _parse_camera_move_packet(self, packet: str) -> bool:
        """
        解析视角移动数据包

        Args:
            packet: 格式化的数据包字符串

        Returns:
            bool: 是否成功解析

        视角移动包载荷长度：10字节
        如果数据包结尾是99 01 00 00，则不分析
        """

        # 提取数据包基本信息
        payload_length, data_hex = self._extract_packet_data_hex(packet)
        if not payload_length or not data_hex:
            return False

        # 检查是否为视角移动数据包
        # 载荷长度应该是10字节 = 20个十六进制字符
        if payload_length != 10:
            return False
        if len(data_hex) < 20:
            return False

        try:
            # 检查数据包结尾，如果是99 01 00 00则不分析
            if len(data_hex) >= 32:  # 确保有足够的长度检查结尾
                packet_end = data_hex[-8:]  # 最后4字节 = 8个十六进制字符
                if packet_end == "99010000":
                    logger.debug("忽略视角移动数据包（特殊结尾）")
                    return False

            # 解析数据包各字段
            # 0-3: 未知字段 (4字节)
            # 4-7: 未知字段 (4字节)
            # 8-11: 未知字段 (4字节)
            # 12-15: X坐标角度 (4字节浮点数，小端序)
            # 16-19: Y坐标角度 (4字节浮点数，小端序)

            # 提取X坐标角度 (float32, 小端序)
            # 位置：数据包的12-15字节（十六进制字符24-32位置）
            x_angle = struct.unpack("<f", bytes.fromhex(data_hex[24:32]))[0]

            # 提取Y坐标角度 (float32, 小端序)
            # 位置：数据包的16-19字节（十六进制字符32-40位置）
            y_angle = struct.unpack("<f", bytes.fromhex(data_hex[32:40]))[0]

            # 记录视角移动数据到文件
            self._write_to_file(
                "camera_moves.txt",
                f"Camera Move: X_angle={x_angle:.4f}, Y_angle={y_angle:.4f}",
            )

            # 插入数据库（需要先创建对应的数据库操作方法）
            success = self.db_ops.insert_camera_move(
                angle_x=x_angle, angle_y=y_angle, packet_source="packet_parser"
            )

            if success:
                logger.debug("视角移动数据已保存到数据库")
            else:
                logger.warning("视角移动数据保存失败")

            return True

        except (ValueError, IndexError, struct.error) as e:
            logger.warning(f"解析视角移动数据包失败: {e}")
            return False

    def _parse_entity_packet(self, packet: str):
        """解析实体数据包（矿物/植物等静态实体）

        Args:
            packet: 格式化的数据包字符串

        Returns:
            bool: 是否成功解析到至少一个实体

        解析的数据包载荷长度：ENTITY_PACKET_LENGTHS
        """
        # 提取出数据流
        payload_length, data_hex = self._extract_packet_data_hex(packet)
        if not payload_length or not data_hex:
            return False

        # 检查是否为实体数据包
        if payload_length not in self.ENTITY_PACKET_LENGTHS:
            return False

        # 提取实体数据
        entities_data = self._extract_entity_data(data_hex)
        if not entities_data:
            return False

        # 处理每个实体
        success_count = 0
        for entity_data in entities_data:
            x, y, index = entity_data
            entity_info = self._generate_entity_info(index)

            # 记录未知ID用于后续分析
            if entity_info["is_unknown"]:
                logger.warning(f"未知实体ID: {index}, 坐标: ({x}, {y})")
            else:
                logger.debug(
                    f"实体映射: {index} -> {entity_info['name']}(阶数:{entity_info.get('maturity_level', 0)})"
                )

            # 将实体信息写入文件
            # formatted_output = self._format_entity_output(entity_info, x, y)
            # self._write_to_file("entity_data.txt", formatted_output)

            # 插入数据库
            # 准备插入实体数据表的字典
            entity_data_dict = {
                "entity_id": index,  # 3021001
                "entity_type": entity_info["type"],  # plant, ore, unknown
                "entity_name": entity_info["name"],  # 聚灵草
                "category": entity_info.get("category"),  # 可能为None 002
                "growth_stage": entity_info.get("growth_stage"),  # 可能为None 1-5
                "maturity_level": entity_info.get("maturity_level", 0),  # 新增：阶数
                "is_mature": entity_info.get("is_mature", False),  # 新增：是否成熟
                "position_x": x,
                "position_y": y,
                "is_unknown": entity_info["is_unknown"],
                "raw_data": None,
            }

            # 插入到实体数据表
            if self.db_ops.insert_entity_data(entity_data_dict):
                logger.debug(
                    f"成功插入实体数据: {entity_info['name']}({index})阶数:{entity_info.get('maturity_level', 0)}"
                )
            else:
                logger.warning(f"插入实体数据失败: {entity_info['name']}({index})")

            # 如果是未知实体，额外记录到未知实体表
            if entity_info["is_unknown"]:
                if self.db_ops.record_unknown_entity(
                    entity_id=index,
                    position_x=x,
                    position_y=y,
                    raw_hex_data=hex(index),  # 将entity_id转为十六进制作为示例
                ):
                    logger.info(f"已记录未知实体: {index}")
                else:
                    logger.warning(f"记录未知实体失败: {index}")

            success_count += 1

        logger.info(f"成功处理 {success_count} 个实体")
        return success_count > 0

    def _extract_entity_data(self, data_hex: str) -> list:
        """从十六进制数据中提取实体信息

        数据格式:
        3122D800 [跳过8字符] [跳过8字符] [跳过8字符] [X坐标] [跳过8字符] [Y坐标] [跳过8字符] [索引] ...

        Args:
            data_hex: 十六进制数据字符串

        Returns:
            list: 实体数据列表，每个元素为 (x, y, index)
        """
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
            if not matches:
                return []

            entities = []
            for match in matches:
                # 字段映射:match[2]=X坐标, match[4]=Y坐标, match[7]=索引
                x_hex, y_hex, index_hex = (
                    match[2],
                    match[4],
                    match[7],
                )

                # 解析
                try:
                    # entity_id = int(bytes.fromhex(entity_id_hex)[::-1].hex(), 16)
                    x = struct.unpack("<f", bytes.fromhex(x_hex))[0]
                    y = struct.unpack("<f", bytes.fromhex(y_hex))[0]

                    # 索引处理：十六进制字符串 -> 字节集 -> 字节集反转(小端转大端) -> 十六进制字符串 -> 十进制整数 -> 字符串
                    # bytes.fromhex(index_hex) - 字节集_十六进制到字节集
                    # [::-1] - 字节集反转
                    # .hex() - 字节集_字节集到十六进制
                    # int(..., 16) - 进制十六到十
                    # str(...) - 到文本
                    index = int(bytes.fromhex(index_hex)[::-1].hex(), 16)

                    # 简化索引解析
                    # index = int(int.from_bytes(bytes.fromhex(index_hex), "little"))

                    entities.append((x, y, index))
                except (ValueError, struct.error) as e:
                    logger.warning(f"解析实体字段失败: {e}")
                    continue

            return entities
        except Exception as e:
            logger.error(f"提取实体数据时出错: {e}")
            return []

    def _generate_entity_info(self, index: int) -> dict:
        """根据实体ID生成实体信息

        Args:
            index: 实体ID 例：3021001

        Returns:
            dict: 包含实体类型、名称等信息的字典
        """
        index_str = str(index)

        # 植物类 (302开头)
        if index_str.startswith("302") and len(index_str) == 7:
            # 解析植物信息
            category = index_str[3:6]  # 中间三位表示种类
            growth_stage = index_str[6]  # 最后一位表示生长状态
            maturity_level = int(index_str[3]) + 1  # 第一位表示阶数-1

            # 从配置文件中获取植物名称
            plant_name = self.plant_mapping.get(category, f"未知植物({category})")

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
            # 解析矿物信息
            mineral_type = index_str[3:]  # 后四位表示矿物种类
            maturity_level = int(index_str[3])  # 第一位表示阶数

            # 从配置文件中获取矿物名称
            mineral_name = self.ore_mapping.get(
                mineral_type, f"未知矿物({mineral_type})"
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
            return {
                "index": index,
                "type": "unknown",
                "category": "unknown",  # 添加默认值
                "name": f"Unknown({index})",
                "is_unknown": True,
                "maturity_level": 0,
                "is_mature": False,
            }

    def _format_entity_output(self, entity_info: dict, x: float, y: float) -> str:
        """格式化实体信息用于输出

        Args:
            entity_info: 实体信息字典
            x: X坐标
            y: Y坐标

        Returns:
            str: 格式化的输出字符串
        """
        # 根据实体类型生成显示名称
        if entity_info["type"] == "plant":
            display_name = f"{entity_info['growth_stage']} {entity_info['name']} {entity_info['growth_stage']}"
        elif entity_info["type"] == "ore":
            display_name = f"{entity_info['category'][0]} {entity_info['name']}"
        else:
            display_name = entity_info["name"]

        return f"Entity ID={entity_info['index']}, Name={display_name}, X={x}, Y={y}"

    # 暂时没用到
    def _write_to_file(self, filename, data):
        """将数据追加到文件

        Args:
            filename: 文件名
            data: 要写入的数据
        """
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"{data}\n")
        except Exception as e:
            logger.error(f"写入文件失败 {filename}: {e}")


if __name__ == "__main__":
    # 创建 PacketParser 实例并传入队列
    parser = PacketParser()

    # 启动解析程序
    parser_thread = threading.Thread(target=parser.parse_packet, daemon=True)
    parser_thread.start()

    try:
        parser_thread.join()  # 等待线程结束
    except KeyboardInterrupt:
        print("解析中止。")
        print("解析中止。")
