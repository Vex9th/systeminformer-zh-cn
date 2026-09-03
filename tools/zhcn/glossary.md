# 术语表 / Glossary（zh-CN）

所有翻译必须遵循本表，保证术语全局一致。表内术语为推荐译法；
同义词一律以本表为准。

## 核心概念

| English | 中文 | 说明 |
|---|---|---|
| process | 进程 | |
| thread | 线程 | |
| handle | 句柄 | |
| service | 服务 | |
| module | 模块 | 进程加载的 DLL/EXE |
| kernel | 内核 | |
| user mode | 用户模式 | 与“内核模式”相对 |
| kernel mode | 内核模式 | |
| token | 令牌 | 访问令牌 |
| privilege | 特权 | 如 SeDebugPrivilege |
| permission | 权限 | |
| integrity level | 完整性级别 | |
| session | 会话 | |
| affinity | 处理器关联 | CPU 亲和性不使用 |
| priority | 优先级 | |
| scheduler | 计划程序 | 线程调度相关 |
| commit charge | 提交内存 | 提交电荷/委托内存不使用 |
| working set | 巩固集内存 | 工作集亦可，保持“工作集”| 
| private bytes | 专用字节 | |
| virtual memory | 虚拟内存 | |
| page file | 页面文件 | |
| heap | 堆 | |
| stack | 堆栈 | 线程调用堆栈 |
| dump | 转储 | 内存转储/崩溃转储 |
| termination / terminate | 终止 | |
| suspend / resume | 挂起 / 恢复 | |
| restart | 重启 | |
| elevator / elevate | 提权 | 以管理员权限运行 |
| run as | 运行身份 | |
| sandbox | 沙盒 | |
| detection | 检测 | |
| provider | 提供程序 | |

## 网络与磁盘

| English | 中文 |
|---|---|
| connection | 连接 |
| listener | 监听 |
| remote address | 远程地址 |
| local address | 本地地址 |
| protocol | 协议 |
| owner | 所有者 |
| total (data rate) | 总计 |
| receive / send | 接收 / 发送 |
| disk | 磁盘 |
| volume | 卷 |
| partition | 分区 |
| physical drive | 物理驱动器 |
| read / write | 读取 / 写入 |
| latency | 延迟 |
| response time | 响应时间 |
| queue depth | 队列深度 |

## UI 词汇

| English | 中文 |
|---|---|
| Properties | 属性 |
| Settings / Options | 设置 |
| Preferences | 首选项 |
| General | 常规 |
| Advanced | 高级 |
| Refresh | 刷新 |
| Copy | 复制 |
| Paste | 粘贴 |
| Save / Save as | 保存 / 另存为 |
| Open | 打开 |
| Browse | 浏览 |
| Close | 关闭 |
| Exit | 退出 |
| OK / Cancel | 确定 / 取消 |
| Yes / No | 是 / 否 |
| Apply | 应用 |
| Reset | 重置 |
| Search / Filter | 搜索 / 筛选 |
| Find | 查找 |
| Replace | 替换 |
| Select all | 全选 |
| invert selection | 反选 |
| Columns | 列 |
| Hide / Show | 隐藏 / 显示 |
| Sort | 排序 |
| Group | 分组 |
| Highlight | 高亮 |
| Tooltip | 工具提示 |
| Details | 详细信息 |
| Summary | 摘要 |
| Statistics | 统计 |
| Legend | 图例 |
| Graph | 图表 |
| Update interval | 刷新间隔 |
| Always on top | 置顶 |
| Minimize to tray | 最小化到托盘 |
| tray icon | 托盘图标 |
| balloon / notification | 通知 |
| plugin | 插件 |

## 系统管理

| English | 中文 |
|---|---|
| job | 作业 |
| job object | 作业对象 |
| environment variable | 环境变量 |
| control panel | 控制面板 |
| device manager | 设备管理器 |
| registry editor | 注册表编辑器 |
| services | 服务 |
| startup | 启动 |
| shutdown / restart | 关机 / 重启 |
| log off | 注销 |
| lock | 锁定 |
| hibernate | 休眠 |
| sleep | 睡眠 |
| user account | 用户账户 |
| group | 组 |
| digital signature | 数字签名 |
| verification / verify | 验证 |
| suspicious | 可疑 |

## 风格约定

1. 快捷键助记符保留在译文中：`&Properties` → `属性(&P)`；括号使用半角。
2. 制表符后的快捷键提示原样保留：`&Rename\tF2` → `重命名(&R)\tF2`。
3. 英文省略号 `...` 保留为 `...`（三个半角句点），与上游一致。
4. 格式占位符（`%s`、`%lu`、`%I64u` 等）数量与类型不得增减、不得改变顺序。
5. 列名、枚举值（如 "Running"、"Stopped"）使用短词，不加“状态”后缀。
6. 危险操作确认文案保持严重语气，不弱化。
7. 产品名 "System Informer" 不翻译。
8. 标点：界面文本使用中文标点（，。：；？！“”（）），但快捷键助记符括号、
   省略号、占位符周围保持半角符号；数字与单位间不加空格（与上游紧凑风格一致）。
9. 单位（KB、MB、GB、ms、μs）保持英文原样。
