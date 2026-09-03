# System Informer 简体中文社区版

[![zh-ci](https://github.com/Vex9th/systeminformer/actions/workflows/zh-cn-build.yml/badge.svg?branch=zh-cn)](https://github.com/Vex9th/systeminformer/actions/workflows/zh-cn-build.yml)

> **本项目是非官方社区 Fork，与 System Informer 官方团队及任何游戏、发行商或反作弊厂商无隶属关系。**

## 项目定位

本项目是 [System Informer](https://github.com/winsiderss/systeminformer) 的简体中文（zh-CN）社区版：

- 基于**最新官方 master** 源码构建，不基于任何旧中文汉化补丁
- 通过**运行时翻译层**（独立语言表 + 英文完整回退）实现本地化，而不是在业务代码里硬编码中文
- 只发布**无驱动的用户态程序**（不构建、不携带 KSystemInformer 内核驱动）
- 不改变程序功能、权限模型、进程操作逻辑与系统访问行为；进程名、窗口类名、服务名与产品元数据均与上游保持一致

## 功能说明

与官方 System Informer 一致（本社区版不增删功能，仅本地化界面）：

- 进程、服务、网络、磁盘、句柄、模块、线程的实时监控与深入检查
- 系统资源图表与统计（CPU、内存、I/O、GPU 等）
- 找出占用资源/锁定文件的进程，结束进程或关闭网络连接
- 带内核模式、WOW64 与 .NET 支持的堆栈跟踪（内核部分需驱动，本构建不可用）
- 超越 services.msc 的服务管理
- 便携免安装，绿色使用

## 截图

> 待补：截图需在真实 Windows 环境运行本程序后截取（主窗口、进程属性、设置页等）。
> 在此之前请以上游 [官方截图](https://github.com/winsiderss/systeminformer#system-informer) 为参考，界面布局与官方版完全一致，文字为简体中文。

## 下载与校验

1. 到 [Releases](https://github.com/Vex9th/systeminformer/releases) 下载 `systeminformer-v*-zh-cn*-portable.zip`（便携版，解压即用）
2. 校验 SHA-256（每个 Release 附有 `SHA256SUMS.txt`，摘要同时写在发布说明中）：

   ```powershell
   Get-FileHash -Algorithm SHA256 .\systeminformer-v...-portable.zip
   ```

3. 解压到任意目录运行 `amd64\SystemInformer.exe`（ARM64 设备用 `arm64\`，32 位系统用 `i386\`）
4. 想恢复英文界面：把设置文件（`SystemInformer.exe.settings.json`）中的 `"Language": "zh-CN"` 改为 `"en"` 后重启程序；未翻译的字符串也会自动显示英文

> 程序未做代码签名，SmartScreen 可能弹出警告；请核对 SHA-256 后选择"仍要运行"，或自行从源码构建。

## 无驱动版本说明

本社区版**只构建用户态程序**：

- 不构建 `KSystemInformer`，不运行 `build_zdriver.cmd`，产物中不含 `.sys`/`.inf`，也不安装任何内核驱动服务
- 依赖内核驱动的高级功能不可用（例如：受保护进程的完整句柄枚举、内核态堆栈采集、驱动级进程保护操作等），界面相应功能会自动回退到用户态方式或显示不可用
- CI 在打包前会**递归检查发布目录，一旦发现 `.sys` 或 `.inf` 立即构建失败**
- 默认关闭内核驱动相关选项（`KsiEnable` 上游默认即为 0；本构建另将驱动告警 `KsiEnableWarnings` 默认关闭，避免无谓弹窗）

## 安全与反作弊兼容性声明

- System Informer 是一款进程/系统检查工具，本身具备读取其他进程信息、结束进程等能力。**部分游戏的反作弊系统可能将此类工具视为可疑软件**，这与是否使用本社区版无关，官方版本同样如此
- **无驱动 ≠ 反作弊白名单**。本构建不含内核驱动，但用户态的进程枚举、句柄查询等行为仍可能触发反作弊检测
- **运行受反作弊保护的游戏期间，请退出本程序**，避免账号或游戏进程被误判处置
- 请从本仓库 Release 或自行构建获取程序，校验 SHA-256，不要使用来历不明的"汉化版"

## 本地化覆盖范围

翻译范围以 CI 每次构建生成的 `coverage-report.md` 为准（Release 附件中提供），覆盖以下界面文字来源：

| 来源 | 说明 |
|---|---|
| 菜单（主菜单/托盘/右键菜单） | 运行时经 PhEMenu 翻译层处理，主程序与全部插件生效 |
| 进程/网络/服务/磁盘等列表列名 | ListView 与 TreeNew 列 |
| 对话框与属性页 | .rc 对话框模板（标题、按钮、分组、静态文本）经模板翻译层处理 |
| 消息框与确认提示 | 消息框、任务对话框、确认对话框及其按钮文字 |
| 状态栏与搜索框 | ToolStatus 插件状态栏模板、各搜索框提示 |
| 插件界面 | ToolStatus、ExtendedTools、ExtendedServices、DotNetTools、HardwareDevices、NetworkTools、OnlineChecks、Updater、UserNotes、WindowExplorer、ExtendedNotifications |

不在翻译范围内：调试类界面（内核调试、syscall 工具）、命令行服务组件（phsvc）、设置文件的 JSON schema 文档等。未翻译字符串自动回退英文。

术语遵循 [tools/zhcn/glossary.md](tools/zhcn/glossary.md)，字符串清单与覆盖率检查见 [tools/zhcn](tools/zhcn/README.md)。

## GitHub Actions 构建

工作流 [`.github/workflows/zh-cn-build.yml`](.github/workflows/zh-cn-build.yml)（与上游 CI 相同的 runner 与步骤，但**不包含任何 driver 任务**）：

- 触发：`workflow_dispatch` 手动运行；`zh-cn` 分支推送做编译验证；`v*-zh-cn*` 标签发布正式版
- 步骤：NuGet 恢复 → `build\build_init.cmd` → `build\build_release.cmd` → 字符串审计与覆盖率检查 → 无驱动断言（递归检查 `.sys`/`.inf`）→ 打包便携 ZIP → 生成 SHA-256 → 创建 Release（附 ZIP、SHA256SUMS、覆盖率报告）
- 所有 Action 固定到官方仓库的具体 commit；权限最小化（仅发布任务 `contents: write`）

## 与上游同步

```bash
git fetch upstream
git checkout zh-cn
git rebase upstream/master
# 重新审计字符串（上游新增的界面文字会出现在清单中）
python3 tools/zhcn/audit.py
python3 tools/zhcn/check_translation.py   # 按报告补翻译
python3 tools/zhcn/generate_translation.py
git push --force-with-lease origin zh-cn
```

本项目的改动集中在 phlib 翻译层、tools/zhcn 工具与少量插桩点，rebase 冲突面很小；上游新增字符串会自动回退英文，不会阻塞同步。

## 已知限制

- **界面文字与布局尚未在真实 Windows 上人工验收**（截断/重叠问题待实测反馈，中文通常短于英文，风险较低）
- 反作弊兼容性无法逐一验证，受保护游戏期间请退出本程序（见上文声明）
- 深层调试功能（内核堆栈、驱动对象详情等）因无驱动而不可用
- 便携版为主；不提供安装器（上游 setup 构建产物不随本社区版发布）
- 自动更新插件指向官方发布渠道，更新后为官方英文版；如需保持中文请从本仓库 Release 手动下载新版

## 上游项目与致谢

- 官方源码：<https://github.com/winsiderss/systeminformer>
- 官方网站：<https://systeminformer.com/>
- 感谢 Winsider Seminars & Solutions, Inc. 与所有上游贡献者（wj32、dmex 等）的杰出工作
- 本项目遵循上游同样的 MIT 许可证（见 [LICENSE.txt](LICENSE.txt)），第三方组件许可见 [COPYRIGHT.txt](COPYRIGHT.txt)

## 许可证

MIT License — 与上游一致。本仓库保留上游全部版权与许可声明；社区版改动同样以 MIT 提供。

本项目是非官方社区 Fork，与 System Informer 官方团队及任何游戏、发行商或反作弊厂商无隶属关系。
