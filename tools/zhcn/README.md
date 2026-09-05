# zh-CN 资源工具

这里放本地化数据、生成器和验证脚本。方案 B 仍在迁移中：当前源码已为主程序、11 个插件、PE Viewer 和安装器生成原生 zh-CN 对话框；已有 969 条动态文字迁到 `STRINGTABLE`，其中 PE Viewer 134 条、安装器 74 条、主程序 312 条、DotNetTools 89 条、ExtendedServices 66 条、ExtendedTools 40 条、ToolStatus 103 条、UserNotes 15 条，HardwareDevices、NetworkTools、OnlineChecks、Updater、WindowExplorer 合计迁移 136 条。审计已修正消息宏参数位置，排除注释死代码，并按 C 编译语义合并相邻字符串、检查格式化后续参数和未解析变量；现又覆盖窗口文字、组合框（含普通字符串数组、带限定符及 `SIP(...)` 初始化的结构体字段数组）及列表分组/项目和包装入口，并将没有运行时翻译 hook 的类别标为必须迁移调用点。修复漏检后新增暴露的 57 条组合框文字已经迁移，服务恢复动作和远程控制热键均改用 item data 保存业务值；ExtendedServices 当前审计项已全部覆盖，DotNetTools 的 8 个 CLR 性能计数器分组及其 81 个计数器项目已全部迁移，WindowExplorer 的 38 个窗口属性分组项和 43 个 UI Automation 属性项，以及主程序、ExtendedTools、WindowExplorer 和 PE Viewer 的其他无共享冲突分组/项目已迁移，NetworkTools 的许可证提示、Ping、Tracert 和 WHOIS 动态窗口文字以及 HardwareDevices 的连接分组、网络状态和适配器详情分组/后备标题也已迁移。审计清单 schema v2 按模块拆分必须迁移的调用点，同一普通字符串仍只保留一个全局翻译单元；模块表按实际出现模块计数，不能与全局翻译单元直接求和。此前被跨模块合并掩盖的 19 个调用点迁移单元现已恢复，项目如实报告 478 条未翻译项。ExtendedServices 触发器编辑器同样已将显示文字与类型、子类型和动作值解耦。早期崩溃提示保留不依赖缓存的静态后备；大量既有文字仍依赖旧兼容翻译层，不能宣称方案 B 整体完成。

## 常用命令

```bash
# 扫描英文源文件，生成临时清单
python3 tools/zhcn/audit.py

# 检查翻译键、占位符和未处理字符串
python3 tools/zhcn/check_translation.py

# 检查旧兼容字符串表是否与翻译数据一致
python3 tools/zhcn/generate_translation.py --check

# 检查 14 个资源宿主的原生对话框和字符串表是否与英文资源同步
python3 tools/zhcn/generate_native_resources.py --check

# 运行源码契约测试
python3 -m unittest discover -s tools/zhcn/tests -v
```

英文 `.rc` 结构或 `zh-CN.json` 发生变化后，重新生成原生资源：

```bash
python3 tools/zhcn/generate_native_resources.py
```

## 文件

| 文件 | 用途 |
|---|---|
| `zh-CN.json` | 当前翻译数据源；`strings` 仍供过渡期运行时字典使用，`native_strings` 只供原生资源使用，不会扩大旧字典 |
| `generate_native_resources.py` | 为主程序、11 个插件和 2 个独立工具生成 `*.zh-cn.rc` |
| `validate_templates.py` | 检查构建后 PE 中的 en-US/zh-CN 对话框、字体和字符串表 ID/占位符 |
| `audit.py` | 扫描主程序、插件和受支持独立工具的英文源文件，不扫描生成的 `*.zh-cn.rc`；输出 schema v2 清单 |
| `translation_contract.py` | 统一定义强制调用点类别、schema 版本和独立模块路径归属 |
| `check_translation.py` | 校验 schema v2，输出缺失键、无用键、占位符错误和按出现模块统计的模块表 |
| `generate_translation.py` | 生成过渡期运行时字典 |
| `tests/` | 源码和生成结果契约测试 |

`manifest.json` 与 `coverage-report.md` 是临时审计输出，只用于列出已扫描入口和剩余缺口，不作为“覆盖率百分比”或发布质量证明。schema v2 不兼容旧清单：`check_translation.py` 会拒绝旧 schema，必须先重新运行 `audit.py`。全局表按翻译单元去重，模块表按模块中的有效出现量统计，两者不能直接求和。macOS 本地检查也不能替代 Windows 的 RC/MSVC 构建、真实运行和视觉验收。
