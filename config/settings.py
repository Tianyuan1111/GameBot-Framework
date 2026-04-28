# config/settings.py

# 游戏服务器IP（目标IP）
SERVER_IP = "159.75.174.141"

# 设置是否启用端口过滤
ENABLE_PORT_FILTER = False  # True/False 如果设置为 False，则不过滤端口

# 目标端口（可以定义多个，使用列表）
CLIENT_PORTS = []

# 是否启用包长度过滤
ENABLE_LENGTHS_FILTER = False

# 允许的包长度（多个长度）（载荷长度）
PACKET_LENGTHS = []
# 空 允许所有数据包通过
# 特定长度的包（允许多个）
# 大于 0 的正整数列表 1, 2, 3, 4, 5 记录所有具有有效负载的包

# 存储路径（可以是数据库，也可以存文件）
# STORE_PATH = "captured_packets.log"
# 暂时没用

# 网卡名
INTERFACE = r"\Device\NPF_{6C579382-45A4-4D5E-B618-3869F4DAA9CD}"
# 在 Windows 上，Scapy 需要使用底层的设备路径名称，而不是普通的接口名称
# 运行interface_selector.py获得设备所有可用接口并选择

# 地图扫描配置
ENABLE_MAP_SCAN = False  # 是否启用地图扫描True/False
SCAN_MAP_ID = "006"  # 默认扫描的地图ID

# 初始坐标设置
INITIAL_X = 0  # 初始X坐标
INITIAL_Y = 0  # 初始Y坐标
