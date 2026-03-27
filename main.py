# main.py

import os
import signal
import threading
import time

from automation.states.map_scanner import MapScanner
from capture.capture_packets import start_sniff
from capture.parse_packets import PacketParser
from config import settings
from database.operations import DatabaseOperations
from web.app import create_app

# 全局标志，用于优雅退出
running = True


def signal_handler(sig, frame):
    global running
    print("\n收到终止信号，正在关闭程序...")
    running = False


# 启动数据包捕获和分析线程
def start_packet_capture():
    """启动数据包捕获和分析"""
    try:
        print("启动数据包捕获...")
        start_sniff()
    except Exception as e:
        print(f"数据包捕获错误: {e}")


def initialize_database():
    """初始化数据库"""
    try:
        print("初始化数据库...")
        # 创建 DatabaseOperations 实例
        db_ops = DatabaseOperations()
        # 调用实例方法清理数据
        db_ops.cleanup_data()
        print("数据库初始化完成！")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        # 根据你的需求决定是否退出程序
        # sys.exit(1)


def start_packet_parsing():
    """启动数据包解析"""
    try:
        print("启动数据包解析...")
        parser = PacketParser()
        parser.parse_packet()  # 直接调用，因为方法内部已经有循环
    except Exception as e:
        print(f"数据包解析错误: {e}")


def run_flask_app(app, host, port, debug_mode):
    """在单独线程中运行Flask应用"""
    try:
        print("=" * 50)
        print("游戏数据仪表板启动中...")
        print(f"访问地址: http://{host}:{port}")
        print(f"调试模式: {debug_mode}")
        print("=" * 50)

        # 注意：在生产环境中不要使用 debug=True
        app.run(host=host, port=port, debug=debug_mode, use_reloader=False)
    except Exception as e:
        print(f"Flask应用启动失败: {e}")


def start_map_scanning():
    """启动地图扫描"""
    try:
        print("启动地图扫描...")
        scanner = MapScanner()

        # 显示可用地图
        scanner.show_available_maps()

        # 从settings获取要扫描的地图
        map_id = settings.SCAN_MAP_ID

        print(f"开始扫描地图: {map_id}")
        success = scanner.start_scan(map_id)

        if success:
            print(f"地图 {map_id} 扫描完成")
        else:
            print(f"地图 {map_id} 扫描失败")

    except Exception as e:
        print(f"地图扫描错误: {e}")


def cleanup_resources():
    """清理资源"""
    print("正在清理资源...")
    # 这里可以添加数据库清理、文件关闭等操作
    # 例如：DatabaseOperations.cleanup()
    time.sleep(1)
    print("资源清理完成")


# 主流程调度
def main():
    """主流程调度"""
    global running

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建线程列表以便管理
    threads = []

    try:
        # 初始化数据库
        initialize_database()

        # 创建Flask应用
        app = create_app()

        # 获取配置
        debug_mode = os.environ.get("DEBUG", "True").lower() == "true"
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", 5000))

        # 启动Flask在单独线程中（避免阻塞主线程）
        flask_thread = threading.Thread(
            target=run_flask_app, args=(app, host, port, debug_mode), daemon=True
        )
        flask_thread.start()
        threads.append(flask_thread)

        # 等待Web服务器启动
        time.sleep(3)

        # 启动数据包解析线程
        parser_thread = threading.Thread(target=start_packet_parsing, daemon=True)
        parser_thread.start()
        threads.append(parser_thread)

        # 短暂延迟确保解析器就绪
        time.sleep(1)

        # 启动数据包捕获线程
        capture_thread = threading.Thread(target=start_packet_capture, daemon=True)
        capture_thread.start()
        threads.append(capture_thread)

        # 从settings获取地图扫描配置
        enable_map_scan = settings.ENABLE_MAP_SCAN

        # 如果启用地图扫描，启动地图扫描线程
        if enable_map_scan:
            print("地图扫描已启用")
            map_scan_thread = threading.Thread(target=start_map_scanning, daemon=True)
            map_scan_thread.start()
            threads.append(map_scan_thread)
        else:
            print(
                "地图扫描未启用，如需启用请在 config/settings.py 中设置 ENABLE_MAP_SCAN = True"
            )

        print("所有服务已启动，程序运行中...")
        print("按 Ctrl+C 退出程序")

        # 主循环，检查线程状态
        while running:
            # 检查是否有线程异常退出
            alive_threads = [t for t in threads if t.is_alive()]

            if not any(alive_threads):
                print("所有工作线程已停止，退出程序")
                break

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行错误: {e}")
    finally:
        running = False
        cleanup_resources()
        print("程序结束")


if __name__ == "__main__":
    main()
