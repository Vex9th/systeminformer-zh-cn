# zh-CN 资源工具

这里放本地化数据、生成器和验证脚本。方案 B 仍在迁移中：当前源码已为主程序、11 个插件、PE Viewer 和安装器生成原生 zh-CN 对话框；已有 729 条动态文字迁到 `STRINGTABLE`，其中 PE Viewer 128 条、安装器 74 条、主程序 290 条、DotNetTools 8 条、ExtendedServices 66 条、ExtendedTools 26 条、ToolStatus 103 条、UserNotes 15 条，HardwareDevices、NetworkTools、OnlineChecks、Updater、WindowExplorer 合计迁移 19 条。审计已修正消息宏参数位置，排除注释死代码，并按 C 编译语义合并相邻字符串、检查格式化后续参数和未解析变量；现又覆盖窗口文字、组合框（含普通字符串数组、带限定符及 `SIP(...)` 初始化的结构体字段数组）及列表分组/项目和包装入口，并将没有运行时翻译 hook 的类别标为必须迁移调用点。修复漏检后新增暴露的 57 条组合框文字已经迁移，服务恢复动作和远程控制热键均改用 item data 保存业务值；ExtendedServices 当前审计项已全部覆盖，主程序、DotNetTools 和 WindowExplorer 又迁移 15 个无共享冲突的列表分组，项目仍如实报告 623 条未翻译项。ExtendedServices 触发器编辑器同样已将显示文字与类型、子类型和动作值解耦。早期崩溃提示保留不依赖缓存的静态后备；大量既有文字仍依赖旧兼容翻译层，不能宣称方案 B 整体完成。

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
| `audit.py` | 扫描主程序、插件和受支持独立工具的英文源文件，不扫描生成的 `*.zh-cn.rc` |
| `check_translation.py` | 输出缺失键、无用键和占位符错误 |
| `generate_translation.py` | 生成过渡期运行时字典 |
| `tests/` | 源码和生成结果契约测试 |

`manifest.json` 与 `coverage-report.md` 是临时审计输出，只用于列出已扫描入口和剩余缺口，不作为“覆盖率百分比”或发布质量证明。macOS 本地检查也不能替代 Windows 的 RC/MSVC 构建、真实运行和视觉验收。
