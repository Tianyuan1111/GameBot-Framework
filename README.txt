game_bot/
├── .vscode/                 # VSCode配置文件
├── capture/                 # 数据捕获部分
│   ├── capture_packets.py       # scapy自动捕获数据包脚本,捕获到的脚本存放到队列，捕获配置在settings.py
│   └── parse_packets.py       	 # 解析数据包，数据插入数据库
├── config/                  # 脚本配置部分
│	├── __init__.py
│   ├── ore_id_mapping.json      # 矿物ID到汉语的映射表
│   ├── plant_id_mapping.json    # 植物ID到汉语的映射表
│   ├── settings.py              # 网络配置参数（端口、IP等），扫描配置
│   ├── auto_config.json         # 自动控制配置
│   └── map_config.json          # 自动控制地图配置 
├── automation/              # 自动控制部分                         
│   ├── core/
│   │   ├── state_machine.py       # 自动机框架（状态调度与转移）
│   │   ├── base_state.py          # 所有状态的基类（定义统一接口）
│   │   ├── transitions.py         # 状态转移条件定义
│   │   └── context.py             # 当前游戏上下文（状态缓存、数据共享）
│   ├── actions/
│   │   ├── move_to.py 
│   │   ├── map_scan.py      
│   │   └── mining.py 
│   ├── states/                    # 具体状态实现
│   │   ├── idle_state.py
│   │   ├── mining_state.py    
│   │   ├── map_scanning.py         # 地图扫描，蛇形扫描算法
│   │   ├── target_selecting.py
│   │   ├── moving_to_target.py    
│   │   ├── mining.py  
│   │   └── error_recovery.py  
│   └── utils/                   
│       └── adb_operations.py    # adb控制
├── database/                # 数据库部分
│   ├── config.py                # 数据库配置
│   ├── models.py                # ORM模型定义
│   ├── manager.py               # 数据库会话管理
│   └── operations.py            # 增删改查接口
├── web/                     # Web 前端部分
│   ├── app.py                   # Flask 后端 API
│   ├── config.py                # 网页配置文件
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       └── main.js
│   └── templates/               # 页面HTML
│       ├── base.html
│       ├── index.html
│       ├── entities.html
│       └── unknown_entities.html
└── main.py                  # 程序入口，调度主流程

capture_packets_tester.py
测试capture_packets.py能否正常运行

parse_packets_tester.py
测试parse_packets.py能否正常运行

interface_selector.py
选择scapy网卡

leidian_coordinate.py
测试屏幕的坐标

ADB_tester.py
测试，筛选ADB移动参数



空闲(IDLE)
    ↓ (网页开始命令)
地图扫描(MAP_SCANNING)
    ↓ (扫描完成)
目标选择(TARGET_SELECTING)
    ↓ (找到目标)
移动到目标(MOVING_TO_TARGET)
    ↓ (到达目标位置)
挖矿(MINING)
    ↓ (挖矿完成)
地图扫描(MAP_SCANNING)  # 循环
    ↓ (没有找到目标)
地图切换(MAP_TRANSITION)
    ↓ (切换完成)
地图扫描(MAP_SCANNING)  # 继续循环



from automation.core.state_machine import StateMachine
from automation.core.context import GameStatus
from automation.states.idle_state import IdleState
from automation.states.map_scanning_state import MapScanningState
from automation.states.target_selecting_state import TargetSelectingState
from automation.states.moving_to_target_state import MovingToTargetState
from automation.states.mining_state import MiningState
from automation.states.map_transition_state import MapTransitionState

# 创建状态机
state_machine = StateMachine()

# 注册所有状态
state_machine.register_state(GameStatus.IDLE, IdleState)
state_machine.register_state(GameStatus.MAP_SCANNING, MapScanningState)
state_machine.register_state(GameStatus.TARGET_SELECTING, TargetSelectingState)
state_machine.register_state(GameStatus.MOVING_TO_TARGET, MovingToTargetState)
state_machine.register_state(GameStatus.MINING, MiningState)
state_machine.register_state(GameStatus.MAP_TRANSITION, MapTransitionState)

# 启动状态机
state_machine.start()



game_bot/
├── src/                           # 源代码主目录（包化）
│   ├── __init__.py
│   ├── __main__.py               # 程序入口
│   ├── core/                     # 核心组件
│   │   ├── __init__.py
│   │   ├── application.py        # 应用主类
│   │   └── exceptions.py         # 自定义异常
│   ├── capture/                  # 数据捕获
│   │   ├── __init__.py
│   │   ├── packet_capture.py     # 数据包捕获
│   │   ├── packet_parser.py      # 数据包解析
│   │   └── models.py             # 数据模型
│   ├── automation/               # 自动控制
│   │   ├── __init__.py
│   │   ├── state_machine.py      # 状态机
│   │   ├── context.py            # 运行上下文
│   │   ├── states/               # 状态实现
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # 状态基类
│   │   │   ├── idle.py
│   │   │   └── mining.py
│   │   └── actions/              # 动作实现
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── movement.py
│   │       └── mining.py
│   ├── database/                 # 数据库
│   │   ├── __init__.py
│   │   ├── manager.py            # 数据库管理
│   │   ├── models.py             # ORM模型
│   │   └── repositories.py       # 数据访问层
│   ├── web/                      # Web界面
│   │   ├── __init__.py
│   │   ├── app.py                # Flask应用
│   │   ├── routes/               # 路由
│   │   │   ├── __init__.py
│   │   │   ├── api.py
│   │   │   └── views.py
│   │   └── static/               # 静态文件
│   │       ├── css/
│   │       └── js/
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       ├── adb.py                # ADB操作
│       ├── logging.py            # 日志配置
│       └── helpers.py            # 辅助函数
├── config/                       # 配置文件
│   ├── __init__.py
│   ├── network.json
│   ├── automation.json
│   ├── database.json
│   ├── ore_id_mapping.json
│   ├── plant_id_mapping.json
│   └── map_config.json
├── data/                         # 数据文件（打包时排除）
│   ├── game_data.db
│   └── logs/
├── tests/                        # 测试代码
│   ├── __init__.py
│   ├── test_capture.py
│   └── test_automation.py
├── docs/                         # 文档
├── scripts/                      # 辅助脚本
│   ├── build.py
│   └── install.py
├── requirements.txt              # 依赖列表
├── setup.py                      # 安装脚本
├── pyproject.toml               # 项目配置
└── README.md