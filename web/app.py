import atexit
import logging
import os
import re
import sys
import json

import pandas as pd
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    Response,
)
from flask.typing import ResponseReturnValue
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from typing import Union, Tuple, Any

from automation.core.context import GameStatus
from automation.core.state_machine import StateMachine
from config import settings
from database.models import EntityData, UnknownEntity
from database.operations import DatabaseOperations

from .config import config

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# 初始化数据库管理器
db_manager = DatabaseOperations()

# 初始化状态机
state_machine = StateMachine()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 创建 logger 对象
logger = logging.getLogger(__name__)

# 全局变量标记状态机是否已启动
_state_machine_started = False

TARGET_CONFIG = {
    "plant_categories": ["402", "403", "401", "408", "308"],
    "ore_categories": ["3003"],
}


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 启动状态机
    def start_state_machine():
        """启动状态机"""
        global _state_machine_started
        try:
            if not _state_machine_started:
                # 注册状态
                from automation.states.idle_state import IdleState
                from automation.states.map_scanning_state import MapScanningState

                state_machine.register_state(GameStatus.IDLE, IdleState)
                state_machine.register_state(GameStatus.MAP_SCANNING, MapScanningState)

                state_machine.start()
                _state_machine_started = True
                logger.info("状态机启动成功")

                # 注册应用退出时的清理函数
                atexit.register(shutdown_state_machine)
        except Exception as e:
            logger.error(f"状态机启动失败: {e}")

    def shutdown_state_machine():
        """停止状态机"""
        global _state_machine_started
        try:
            if _state_machine_started and state_machine:
                state_machine.stop()
                _state_machine_started = False
                logger.info("状态机已停止")
        except Exception as e:
            logger.error(f"停止状态机时发生错误: {e}")

    # 应用启动时启动状态机
    first_request_handled = False

    @app.before_request
    def initialize_app():
        nonlocal first_request_handled
        if not first_request_handled:
            start_state_machine()
            first_request_handled = True

    @app.route("/")
    def index():
        """仪表板首页"""
        return render_template("index.html")

    @app.route("/entities")
    def entities():
        """实体数据页面"""
        try:
            # 获取查询参数
            display_mode = request.args.get("display_mode", "all")
            maturity_level = int(request.args.get("maturity_level", 1))

            # 根据显示模式获取数据
            if display_mode == "mature":
                # 显示N阶及以上成熟植物和矿物
                entities_list = db_manager.get_entities_by_maturity_and_type(
                    min_maturity=maturity_level,
                    entity_types=["plant", "ore"],
                    exclude_unknown=True,
                )
            elif display_mode == "ores_only":
                # 只显示N阶矿物
                entities_list = db_manager.get_ores_by_maturity(
                    min_maturity=maturity_level
                )
            else:
                # 显示所有实体（默认）
                entities_list = db_manager.get_all_entities_dict()

            # 转换为DataFrame进行统计
            df = pd.DataFrame(entities_list) if entities_list else pd.DataFrame()

            # 实体类型统计
            entity_stats = (
                df["entity_type"].value_counts().to_dict() if not df.empty else {}
            )

            return render_template(
                "entities.html",
                data=entities_list,
                stats=entity_stats,
                display_mode=display_mode,
                maturity_level=maturity_level,
            )

        except Exception as e:
            logger.error(f"获取实体数据失败: {e}")
            return render_template(
                "entities.html", data=[], stats={}, display_mode="all", maturity_level=1
            )

    @app.route("/unknown_entities")
    def unknown_entities():
        """未知实体页面"""
        try:
            # 使用ORM方法获取数据
            unknown_entities_list = db_manager.get_unknown_entities()

            # 转换为字典列表
            data_dicts = [entity.to_dict() for entity in unknown_entities_list]

            # 如果需要DataFrame格式
            df = pd.DataFrame(data_dicts)

            # 安全地处理数据转换
            if df is not None and not df.empty:
                data = df.to_dict("records")
            else:
                data = []

            return render_template("unknown_entities.html", data=data)
        except Exception as e:
            logger.error(f"获取未知实体页面数据失败: {e}")
            return render_template("unknown_entities.html", data=[])

    @app.route("/config", methods=["GET", "POST"])
    def config_page():
        """配置页面"""
        if request.method == "POST":
            # 检查是否是地图配置操作
            if request.form.get("action") == "save_map_config":
                return save_map_config()
            elif request.form.get("action") == "delete_map":
                return delete_map()
            elif request.form.get("action") == "set_default_map":
                return set_default_map()

            try:
                # 获取表单数据
                new_config = {
                    "SERVER_IP": request.form.get("server_ip", ""),
                    "ENABLE_PORT_FILTER": request.form.get("enable_port_filter")
                    == "true",
                    "ENABLE_LENGTHS_FILTER": request.form.get("enable_lengths_filter")
                    == "true",
                    "ENABLE_MAP_SCAN": request.form.get("enable_map_scan") == "true",
                    "SCAN_MAP_ID": request.form.get("scan_map_id", ""),
                    "INITIAL_X": int(request.form.get("initial_x", 0)),
                    "INITIAL_Y": int(request.form.get("initial_y", 0)),
                    "INTERFACE": request.form.get("interface", ""),
                }

                # 处理端口列表
                client_ports = request.form.get("client_ports", "")
                new_config["CLIENT_PORTS"] = [
                    int(port.strip())
                    for port in client_ports.split(",")
                    if port.strip().isdigit()
                ]

                # 处理包长度列表
                packet_lengths = request.form.get("packet_lengths", "")
                new_config["PACKET_LENGTHS"] = [
                    int(length.strip())
                    for length in packet_lengths.split(",")
                    if length.strip().isdigit()
                ]

                # 保存配置到文件
                save_config_to_file(new_config)
                # 更新当前运行的配置
                update_runtime_config(new_config)
                flash("配置已成功保存！", "success")
                logger.info("配置已更新并保存到文件")

            except Exception as e:
                flash(f"更新配置失败: {str(e)}", "error")
                logger.error(f"更新配置失败: {e}")

            return redirect(url_for("config_page"))

        # GET请求，显示当前配置
        config_data = get_current_config()

        # 读取地图配置文件
        map_config = load_map_config()

        return render_template("config.html", config=config_data, map_config=map_config)

    def save_map_config():
        """保存地图配置到文件"""
        try:
            map_id = request.form.get("map_id")
            map_name = request.form.get("map_name")
            map_width = int(request.form.get("map_width", 0))
            map_height = int(request.form.get("map_height", 0))

            # 验证输入
            if not map_name or map_width <= 0 or map_height <= 0:
                flash("地图名称、宽度和高度必须填写且为有效值！", "error")
                return redirect(url_for("config_page"))

            # 读取现有配置
            map_config = load_map_config()

            if map_id:  # 更新现有地图
                if map_id in map_config["maps"]:
                    map_config["maps"][map_id] = {
                        "map_name": map_name,
                        "map_width": map_width,
                        "map_height": map_height,
                    }
                    flash(f"地图 {map_name} 已更新！", "success")
                    logger.info(f"地图配置已更新: {map_id} - {map_name}")
                else:  # 新增指定ID的地图
                    map_config["maps"][map_id] = {
                        "map_name": map_name,
                        "map_width": map_width,
                        "map_height": map_height,
                    }
                    flash(f"地图 {map_name} 已创建！", "success")
                    logger.info(f"新地图配置已创建: {map_id} - {map_name}")
            else:  # 新建地图，自动生成ID
                # 找到最大的地图ID并递增
                existing_ids = [
                    int(mid) for mid in map_config["maps"].keys() if mid.isdigit()
                ]
                new_id_num = max(existing_ids) + 1 if existing_ids else 1
                new_id = f"{new_id_num:03d}"

                map_config["maps"][new_id] = {
                    "map_name": map_name,
                    "map_width": map_width,
                    "map_height": map_height,
                }
                flash(f"地图 {map_name} 已创建，ID: {new_id}！", "success")
                logger.info(f"新地图配置已创建: {new_id} - {map_name}")

            # 如果没有默认地图，设置第一个地图为默认
            if not map_config.get("default_map") and map_config["maps"]:
                map_config["default_map"] = next(iter(map_config["maps"].keys()))

            # 保存到文件
            save_map_config_to_file(map_config)

        except ValueError as e:
            flash("地图宽度和高度必须为有效的数字！", "error")
            logger.error(f"地图配置数值错误: {e}")
        except Exception as e:
            flash(f"保存地图配置失败: {str(e)}", "error")
            logger.error(f"保存地图配置失败: {e}")

        return redirect(url_for("config_page"))

    def delete_map():
        """删除地图配置"""
        try:
            map_id = request.form.get("map_id")

            if not map_id:
                flash("地图ID不能为空！", "error")
                return redirect(url_for("config_page"))

            # 读取现有配置
            map_config = load_map_config()

            if map_id in map_config["maps"]:
                map_name = map_config["maps"][map_id]["map_name"]
                del map_config["maps"][map_id]

                # 如果删除的是默认地图，重置默认地图
                if map_config.get("default_map") == map_id:
                    if map_config["maps"]:
                        map_config["default_map"] = next(
                            iter(map_config["maps"].keys())
                        )
                    else:
                        map_config["default_map"] = ""

                # 保存到文件
                save_map_config_to_file(map_config)
                flash(f"地图 {map_name} 已删除！", "success")
                logger.info(f"地图配置已删除: {map_id} - {map_name}")
            else:
                flash("地图不存在！", "error")

        except Exception as e:
            flash(f"删除地图失败: {str(e)}", "error")
            logger.error(f"删除地图失败: {e}")

        return redirect(url_for("config_page"))

    def set_default_map():
        """设置默认地图"""
        try:
            map_id = request.form.get("map_id")

            if not map_id:
                flash("地图ID不能为空！", "error")
                return redirect(url_for("config_page"))

            # 读取现有配置
            map_config = load_map_config()

            if map_id in map_config["maps"]:
                map_config["default_map"] = map_id
                map_name = map_config["maps"][map_id]["map_name"]

                # 保存到文件
                save_map_config_to_file(map_config)
                flash(f"已将 {map_name} 设置为默认地图！", "success")
                logger.info(f"默认地图已设置为: {map_id} - {map_name}")
            else:
                flash("地图不存在！", "error")

        except Exception as e:
            flash(f"设置默认地图失败: {str(e)}", "error")
            logger.error(f"设置默认地图失败: {e}")

        return redirect(url_for("config_page"))

    def load_map_config():
        """加载地图配置文件"""
        try:
            config_path = get_map_config_path()

            # 如果配置文件不存在，创建默认配置
            if not os.path.exists(config_path):
                default_config = {
                    "maps": {
                        "001": {
                            "map_name": "十万大山",
                            "map_width": 335,
                            "map_height": 285,
                        },
                        "002": {
                            "map_name": "云梦泽",
                            "map_width": 285,
                            "map_height": 240,
                        },
                        "003": {
                            "map_name": "极寒山脉",
                            "map_width": 335,
                            "map_height": 285,
                        },
                        "004": {
                            "map_name": "昆吾圣山",
                            "map_width": 385,
                            "map_height": 385,
                        },
                        "005": {
                            "map_name": "上古战场",
                            "map_width": 382,
                            "map_height": 383,
                        },
                        "006": {
                            "map_name": "极西之地",
                            "map_width": 383,
                            "map_height": 383,
                        },
                        "007": {
                            "map_name": "天都山脉",
                            "map_width": 285,
                            "map_height": 285,
                        },
                        "008": {
                            "map_name": "北冥冰原",
                            "map_width": 238,
                            "map_height": 238,
                        },
                    },
                    "default_map": "004",
                }
                # 确保配置目录存在
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                save_map_config_to_file(default_config)
                return default_config

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 确保配置结构完整
            if "maps" not in config:
                config["maps"] = {}
            if "default_map" not in config:
                config["default_map"] = ""

            return config

        except Exception as e:
            logger.error(f"加载地图配置失败: {e}")
            # 返回空配置而不是崩溃
            return {"maps": {}, "default_map": ""}

    def save_map_config_to_file(config):
        """保存地图配置到文件"""
        try:
            config_path = get_map_config_path()

            # 确保配置目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            logger.info(f"地图配置已保存到: {config_path}")

        except Exception as e:
            logger.error(f"保存地图配置到文件失败: {e}")
            raise

    def get_map_config_path():
        """获取地图配置文件路径"""
        return os.path.join("config", "map_config.json")

    # 确保在应用启动时加载地图配置
    def init_map_config():
        """初始化地图配置"""
        try:
            map_config = load_map_config()
            logger.info(f"地图配置初始化完成，共加载 {len(map_config['maps'])} 个地图")
            return map_config
        except Exception as e:
            logger.error(f"地图配置初始化失败: {e}")
            return {"maps": {}, "default_map": ""}

    # 在应用启动时调用初始化
    # map_config = init_map_config()

    def save_config_to_file(new_config):
        """将配置保存到 settings.py 文件"""
        settings_file_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "settings.py"
        )
        settings_file_path = os.path.abspath(settings_file_path)

        # 读取原始文件内容
        with open(settings_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 更新每个配置项
        for key, value in new_config.items():
            if isinstance(value, str):
                replacement = f'{key} = "{value}"'
            elif isinstance(value, bool):
                replacement = f"{key} = {str(value)}"
            elif isinstance(value, list):
                if value:
                    replacement = f"{key} = {value}"
                else:
                    replacement = f"{key} = []"
            elif isinstance(value, int):
                replacement = f"{key} = {value}"
            else:
                replacement = f"{key} = {repr(value)}"

            # 使用正则表达式替换配置项
            pattern = rf"^{key}\s*=.*$"
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # 写回文件
        with open(settings_file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def update_runtime_config(new_config):
        """更新当前运行时的配置"""
        for key, value in new_config.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

    def get_current_config():
        """获取当前配置"""
        return {
            "SERVER_IP": settings.SERVER_IP,
            "ENABLE_PORT_FILTER": settings.ENABLE_PORT_FILTER,
            "CLIENT_PORTS": ", ".join(map(str, settings.CLIENT_PORTS)),
            "ENABLE_LENGTHS_FILTER": settings.ENABLE_LENGTHS_FILTER,
            "PACKET_LENGTHS": ", ".join(map(str, settings.PACKET_LENGTHS)),
            "ENABLE_MAP_SCAN": settings.ENABLE_MAP_SCAN,
            "SCAN_MAP_ID": settings.SCAN_MAP_ID,
            "INITIAL_X": settings.INITIAL_X,
            "INITIAL_Y": settings.INITIAL_Y,
            "INTERFACE": settings.INTERFACE,
        }

    @app.route("/api/target-categories", methods=["GET", "POST", "DELETE"])
    def api_target_categories() -> ResponseReturnValue:
        """API: 管理目标分类配置"""
        global TARGET_CONFIG

        try:
            if request.method == "GET":
                return jsonify(TARGET_CONFIG)

            elif request.method == "POST":
                data = request.get_json()
                if not data:
                    return jsonify({"error": "无效的请求数据"}), 400

                # 验证数据格式
                plant_categories = data.get("plant_categories")
                ore_categories = data.get("ore_categories")

                if plant_categories is not None:
                    if not isinstance(plant_categories, list):
                        return jsonify({"error": "plant_categories必须是列表"}), 400
                    TARGET_CONFIG["plant_categories"] = plant_categories

                if ore_categories is not None:
                    if not isinstance(ore_categories, list):
                        return jsonify({"error": "ore_categories必须是列表"}), 400
                    TARGET_CONFIG["ore_categories"] = ore_categories

                logger.info(
                    f"目标分类配置已更新: 植物{len(TARGET_CONFIG['plant_categories'])}个, 矿物{len(TARGET_CONFIG['ore_categories'])}个"
                )
                return jsonify({"message": "配置更新成功"})

            elif request.method == "DELETE":
                data = request.get_json()
                if not data:
                    return jsonify({"error": "无效的请求数据"}), 400

                category_type = data.get("type")
                category_id = data.get("id")

                if not category_type or not category_id:
                    return jsonify({"error": "缺少参数"}), 400

                if category_type == "plant":
                    if category_id in TARGET_CONFIG["plant_categories"]:
                        TARGET_CONFIG["plant_categories"].remove(category_id)
                        return jsonify({"message": "删除成功"})
                    else:
                        return jsonify({"error": "分类不存在"}), 404

                elif category_type == "ore":
                    if category_id in TARGET_CONFIG["ore_categories"]:
                        TARGET_CONFIG["ore_categories"].remove(category_id)
                        return jsonify({"message": "删除成功"})
                    else:
                        return jsonify({"error": "分类不存在"}), 404

                else:
                    return jsonify({"error": "无效的类型"}), 400
            else:
                # 处理不支持的 HTTP 方法
                return jsonify({"error": "不支持的请求方法"}), 405

        except Exception as e:
            logger.error(f"目标分类管理异常: {e}")
            return jsonify({"error": "服务器内部错误"}), 500

    @app.route("/api/stats")
    def api_stats():
        """API: 获取实体统计数据"""
        try:
            stats = {}
            session = db_manager.get_session()

            try:

                # 使用全局配置中的分类
                PLANT_CATEGORIES = TARGET_CONFIG["plant_categories"]
                ORE_CATEGORIES = TARGET_CONFIG["ore_categories"]

                # 基础统计
                total_plants = (
                    session.query(EntityData)
                    .filter(
                        EntityData.entity_type == "plant",
                        EntityData.category.in_(PLANT_CATEGORIES),
                    )
                    .count()
                )

                total_ores = (
                    session.query(EntityData)
                    .filter(
                        EntityData.entity_type == "ore",
                        EntityData.category.in_(ORE_CATEGORIES),
                    )
                    .count()
                )

                # 基础统计
                stats["summary"] = {
                    "total_entities": session.query(EntityData).count(),
                    "total_unknown_entities": session.query(UnknownEntity).count(),
                    "total_plants": total_plants,
                    "total_ores": total_ores,
                    "unique_entity_types": session.query(EntityData.entity_type)
                    .distinct()
                    .count(),
                    "unique_categories": session.query(EntityData.category)
                    .distinct()
                    .count(),
                }

                # 获取过滤后的实体数据用于表格显示（限制数量避免性能问题）
                entities_data = (
                    session.query(EntityData)
                    .filter(
                        (
                            (EntityData.entity_type == "plant")
                            & (EntityData.category.in_(PLANT_CATEGORIES))
                        )
                        | (
                            (EntityData.entity_type == "ore")
                            & (EntityData.category.in_(ORE_CATEGORIES))
                        )
                    )
                    .order_by(EntityData.timestamp.desc())
                    .limit(100)  # 限制显示数量，可以根据需要调整
                    .all()
                )

                # 转换为字典格式
                stats["entities_data"] = [entity.to_dict() for entity in entities_data]

                # 植物分布统计
                plants_distribution = (
                    session.query(EntityData.entity_name, func.count(EntityData.id))
                    .filter(
                        EntityData.entity_type == "plant",
                        EntityData.category.in_(PLANT_CATEGORIES),
                    )
                    .group_by(EntityData.entity_name)
                    .all()
                )
                stats["plants_distribution"] = {
                    entity_name: count for entity_name, count in plants_distribution
                }

                # 矿物分布统计
                ores_distribution = (
                    session.query(EntityData.entity_name, func.count(EntityData.id))
                    .filter(
                        EntityData.entity_type == "ore",
                        EntityData.category.in_(ORE_CATEGORIES),
                    )
                    .group_by(EntityData.entity_name)
                    .all()
                )
                stats["ores_distribution"] = {
                    entity_name: count for entity_name, count in ores_distribution
                }

                # 植物位置数据（用于散点图）
                plants_locations = {}
                plant_locations_data = (
                    session.query(
                        EntityData.entity_name,
                        EntityData.position_x,
                        EntityData.position_y,
                    )
                    .filter(
                        EntityData.entity_type == "plant",
                        EntityData.category.in_(PLANT_CATEGORIES),
                    )
                    .all()
                )

                for name, x, y in plant_locations_data:
                    if name not in plants_locations:
                        plants_locations[name] = []
                    plants_locations[name].append({"x": x, "y": y})

                stats["plants_locations"] = plants_locations

                # 矿物位置数据（用于散点图）
                ores_locations = {}
                ore_locations_data = (
                    session.query(
                        EntityData.entity_name,
                        EntityData.position_x,
                        EntityData.position_y,
                    )
                    .filter(
                        EntityData.entity_type == "ore",
                        EntityData.category.in_(ORE_CATEGORIES),
                    )
                    .all()
                )

                for name, x, y in ore_locations_data:
                    if name not in ores_locations:
                        ores_locations[name] = []
                    ores_locations[name].append({"x": x, "y": y})

                stats["ores_locations"] = ores_locations

            except SQLAlchemyError as e:
                logger.error(f"查询实体统计数据失败: {e}")
                return jsonify({"error": "获取统计数据失败"}), 500

            finally:
                session.close()

            return jsonify(stats)

        except Exception as e:
            logger.error(f"API统计接口异常: {e}")
            return jsonify({"error": "服务器内部错误"}), 500

    # ==================== 状态机路由 ====================

    @app.route("/state_machine")
    def state_machine_control():
        """状态机控制页面"""
        try:
            # 获取所有可用的状态
            state_list = list(GameStatus)

            # 获取当前状态
            status = state_machine.get_status_for_web() if state_machine else {}

            return render_template(
                "state_machine.html", state_list=state_list, status=status
            )
        except Exception as e:
            logger.error(f"状态机控制页面加载失败: {e}")
            flash("状态机控制页面加载失败", "error")
            return redirect(url_for("index"))

    @app.route("/state_machine/status", methods=["GET"])
    def get_state_machine_status():
        """获取状态机状态 API"""
        try:
            if not state_machine or not _state_machine_started:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "状态机未初始化或未启动",
                            "status": {
                                "current_state": "NOT_STARTED",
                                "target_state": "NOT_STARTED",
                                "is_running": False,
                                "is_paused": False,
                            },
                        }
                    ),
                    500,
                )

            status = state_machine.get_status_for_web()
            return jsonify({"success": True, "status": status})
        except Exception as e:
            logger.error(f"获取状态机状态失败: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/state_machine/set_target_state", methods=["POST"])
    def set_target_state():
        """设置目标状态 API"""
        try:
            data = request.get_json()
            state_str = data.get("state")

            if not state_str:
                return jsonify({"success": False, "message": "未提供状态参数"}), 400

            success = state_machine.set_target_state_from_web(state_str)

            if success:
                return jsonify(
                    {"success": True, "message": f"目标状态已设置为 {state_str}"}
                )
            else:
                return (
                    jsonify({"success": False, "message": f"无效的状态: {state_str}"}),
                    400,
                )

        except Exception as e:
            logger.error(f"设置目标状态失败: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/state_machine/force_state_change", methods=["POST"])
    def force_state_change():
        """强制状态切换 API"""
        try:
            data = request.get_json()
            state_str = data.get("state")

            if not state_str:
                return jsonify({"success": False, "message": "未提供状态参数"}), 400

            success = state_machine.force_state_change_from_web(state_str)

            if success:
                return jsonify(
                    {"success": True, "message": f"已强制切换到 {state_str} 状态"}
                )
            else:
                return (
                    jsonify({"success": False, "message": f"无效的状态: {state_str}"}),
                    400,
                )

        except Exception as e:
            logger.error(f"强制状态切换失败: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/state_machine/pause", methods=["POST"])
    def pause_state_machine():
        """暂停状态机 API"""
        try:
            state_machine.pause_from_web()
            return jsonify({"success": True, "message": "状态机已暂停"})
        except Exception as e:
            logger.error(f"暂停状态机失败: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/state_machine/resume", methods=["POST"])
    def resume_state_machine():
        """恢复状态机 API"""
        try:
            state_machine.resume_from_web()
            return jsonify({"success": True, "message": "状态机已恢复"})
        except Exception as e:
            logger.error(f"恢复状态机失败: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/state_machine/emergency_stop", methods=["POST"])
    def emergency_stop():
        """紧急停止 API"""
        try:
            state_machine.emergency_stop_from_web()
            return jsonify({"success": True, "message": "紧急停止命令已发送"})
        except Exception as e:
            logger.error(f"紧急停止失败: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
