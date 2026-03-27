# interface_selector.py

import os
import sys
import json
import wmi

from config.settings import INTERFACE

# 添加项目根目录到路径，确保可以导入配置
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def get_network_interfaces_wmi():
    """
    使用WMI获取已启用的网络接口详细信息
    """
    interfaces_info = []

    try:
        # 连接到WMI
        c = wmi.WMI()

        print("正在获取网络接口信息...")

        # 获取所有网络适配器
        for adapter in c.Win32_NetworkAdapter():
            # 获取对应的网络适配器配置信息
            configs = c.Win32_NetworkAdapterConfiguration(Index=adapter.Index)
            config = configs[0] if configs else None

            # 只处理已启用IP的接口
            if not config or not getattr(config, "IPEnabled", False):
                continue

            # 安全地获取IP地址
            ip_addresses = []
            if config and hasattr(config, "IPAddress") and config.IPAddress:
                ip_addresses = config.IPAddress

            # 安全地获取MAC地址
            mac_address = "N/A"
            if config and hasattr(config, "MACAddress") and config.MACAddress:
                mac_address = config.MACAddress

            interface_info = {
                "name": adapter.Name if adapter.Name else "Unknown",
                "description": (
                    adapter.Description if adapter.Description else "Unknown"
                ),
                "interface_type": (
                    adapter.AdapterType if adapter.AdapterType else "Unknown"
                ),
                "device_id": adapter.DeviceID,
                "guid": adapter.GUID if adapter.GUID else "N/A",
                "mac_address": mac_address,
                "ip_addresses": ip_addresses,
                "ip_enabled": config.IPEnabled if config else False,
                "adapter_status": (
                    adapter.NetConnectionStatus if adapter.NetConnectionStatus else 0
                ),
                "product_name": adapter.ProductName if adapter.ProductName else "N/A",
                "service_name": adapter.ServiceName if adapter.ServiceName else "N/A",
                "manufacturer": adapter.Manufacturer if adapter.Manufacturer else "N/A",
                "scapy_interface": (
                    r"\Device\NPF_{" + adapter.GUID.strip("{}") + "}"
                    if adapter.GUID
                    else "N/A"
                ),
            }
            interfaces_info.append(interface_info)

    except Exception as e:
        print("WMI查询失败: {}".format(e))
        return []

    return interfaces_info


def get_connection_status(status_code):
    """
    将连接状态代码转换为可读文本
    """
    status_map = {
        0: "已断开",
        1: "连接中",
        2: "已连接",
        3: "断开中",
        4: "硬件不存在",
        5: "硬件禁用",
        6: "硬件故障",
        7: "媒体断开",
        8: "正在验证",
        9: "验证成功",
        10: "验证失败",
        11: "连接中(等待用户)",
        12: "连接中(等待配置)",
        13: "连接中(等待呼叫)",
        14: "连接中(等待重拨)",
        15: "连接中(等待回拨)",
        16: "连接中(等待提升)",
        17: "连接中(等待重启)",
        18: "连接中(等待认证)",
        19: "连接中(等待重新认证)",
    }
    return status_map.get(status_code, "未知状态({})".format(status_code))


def display_interfaces_info(interfaces=None):
    """
    显示已启用的网络接口信息
    """
    if interfaces is None:
        interfaces = get_network_interfaces_wmi()

    print("=" * 100)
    print("Windows网络接口信息 (仅显示已启用的接口)")
    print("=" * 100)

    if not interfaces:
        print("未找到已启用的网络接口")
        return []

    # 按设备ID排序
    interfaces.sort(key=lambda x: int(x["device_id"]))

    for i, interface in enumerate(interfaces, 1):
        print("\n接口 #{}:".format(i))
        print("  ┌─ 基本信息")
        print("  │  名称: {}".format(interface["name"]))
        print("  │  描述: {}".format(interface["description"]))
        print("  │  产品: {}".format(interface["product_name"]))
        print("  │  制造商: {}".format(interface["manufacturer"]))

        print("  ├─ 技术信息")
        print("  │  类型: {}".format(interface["interface_type"]))
        print("  │  服务名: {}".format(interface["service_name"]))

        print("  ├─ 标识信息")
        print("  │  设备ID: {}".format(interface["device_id"]))
        print("  │  GUID: {}".format(interface["guid"]))
        print("  │  Scapy接口: {}".format(interface["scapy_interface"]))

        print("  ├─ 网络信息")
        print("  │  MAC地址: {}".format(interface["mac_address"]))

        # IP地址信息
        ip_addresses = interface["ip_addresses"]
        if ip_addresses and len(ip_addresses) > 0:
            # 过滤掉IPv6链路本地地址
            ipv4_addresses = [ip for ip in ip_addresses if ":" not in ip]
            ipv6_addresses = [
                ip for ip in ip_addresses if ":" in ip and not ip.startswith("fe80::")
            ]

            if ipv4_addresses:
                print("  │  IPv4地址: {}".format(", ".join(ipv4_addresses)))
            if ipv6_addresses:
                print("  │  IPv6地址: {}".format(", ".join(ipv6_addresses)))
        else:
            print("  │  IP地址: 未配置")

        print("  └─ 状态信息")
        status_text = get_connection_status(interface["adapter_status"])
        print("      连接状态: {}".format(status_text))

    print("\n" + "=" * 100)
    print("总计: {} 个已启用的网络接口".format(len(interfaces)))
    print("=" * 100)

    return interfaces


def update_settings_interface(interface_path):
    """
    更新settings.py中的INTERFACE配置
    """
    settings_path = os.path.join(project_root, "config", "settings.py")

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 替换INTERFACE的值
        new_content = content.replace(
            f'INTERFACE = "{INTERFACE}"', f'INTERFACE = "{interface_path}"'
        )

        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"成功更新网卡配置: {interface_path}")
        return True

    except Exception as e:
        print(f"更新配置失败: {e}")
        return False


def select_interface_interactive():
    """
    交互式选择网卡接口
    """
    interfaces = get_network_interfaces_wmi()

    if not interfaces:
        print("错误: 未找到任何已启用的网络接口")
        return None

    display_interfaces_info(interfaces)

    while True:
        try:
            choice = input(
                f"\n请选择网卡接口 (1-{len(interfaces)}) 或输入 'q' 退出: "
            ).strip()

            if choice.lower() == "q":
                return None

            choice_num = int(choice)
            if 1 <= choice_num <= len(interfaces):
                selected_interface = interfaces[choice_num - 1]
                scapy_interface = selected_interface["scapy_interface"]

                if scapy_interface == "N/A":
                    print("错误: 所选接口没有有效的GUID，无法用于Scapy")
                    continue

                print(f"\n已选择: {selected_interface['name']}")
                print(f"Scapy接口路径: {scapy_interface}")

                # 更新配置
                if update_settings_interface(scapy_interface):
                    return selected_interface
                else:
                    return None
            else:
                print(f"请输入 1-{len(interfaces)} 之间的数字")

        except ValueError:
            print("请输入有效的数字")
        except Exception as e:
            print(f"选择过程中发生错误: {e}")
            return None


def get_interfaces_for_web():
    """
    为网页端提供接口列表
    """
    interfaces = get_network_interfaces_wmi()

    # 转换为网页友好的格式
    web_interfaces = []
    for i, interface in enumerate(interfaces, 1):
        web_interface = {
            "index": i,
            "name": interface["name"],
            "description": interface["description"],
            "ip_addresses": interface["ip_addresses"],
            "scapy_interface": interface["scapy_interface"],
            "guid": interface["guid"],
        }
        web_interfaces.append(web_interface)

    return web_interfaces


def update_interface_from_web(interface_index):
    """
    从网页端更新接口配置
    """
    interfaces = get_network_interfaces_wmi()

    if not interfaces or interface_index < 1 or interface_index > len(interfaces):
        return False, "无效的接口索引"

    selected_interface = interfaces[interface_index - 1]
    scapy_interface = selected_interface["scapy_interface"]

    if scapy_interface == "N/A":
        return False, "所选接口没有有效的GUID"

    if update_settings_interface(scapy_interface):
        return True, f"成功切换到: {selected_interface['name']}"
    else:
        return False, "更新配置失败"


def check_and_select_interface():
    """
    检查并选择接口（主程序调用）
    """
    # 检查当前配置是否为空
    if not INTERFACE or INTERFACE == "":
        print("检测到首次运行，需要配置网卡接口...")
        return select_interface_interactive()
    else:
        print(f"使用已配置的网卡接口: {INTERFACE}")
        return None


def main():
    """
    主函数 - 独立运行时的入口
    """
    try:
        import wmi
    except ImportError:
        print("错误: 请安装wmi库")
        print("安装命令: pip install wmi")
        return

    print("网卡接口选择器 (独立模式)")
    print("当前配置:", f"'{INTERFACE}'" if INTERFACE else "未配置")

    if INTERFACE:
        print("\n当前已配置网卡接口，是否重新选择? (y/n)")
        choice = input().strip().lower()
        if choice != "y":
            return

    select_interface_interactive()


if __name__ == "__main__":
    main()


# 在main.py中
# from capture.interface_selector import check_and_select_interface

# 程序启动时检查
# check_and_select_interface()


# 在web/app.py中添加路由
# from capture.interface_selector import get_interfaces_for_web, update_interface_from_web

# @app.route('/api/interfaces')
# get_interfaces():
# return jsonify(get_interfaces_for_web())

# @app.route('/api/select_interface', methods=['POST'])
# def select_interface():
# index = request.json.get('index')
# success, message = update_interface_from_web(index)
# return jsonify({'success': success, 'message': message})
