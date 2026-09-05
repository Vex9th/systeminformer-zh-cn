# System Informer 简体中文社区版

[![zh-ci](https://github.com/Vex9th/systeminformer-zh-cn/actions/workflows/zh-cn-build.yml/badge.svg?branch=zh-cn)](https://github.com/Vex9th/systeminformer-zh-cn/actions/workflows/zh-cn-build.yml)

System Informer 的非官方简体中文、无驱动便携构建。程序名为 `sys_info.exe`，可与官方版并存。

## 下载

从 [Releases](https://github.com/Vex9th/systeminformer-zh-cn/releases) 下载便携包，解压后运行：

- 64 位 Windows：`amd64\sys_info.exe`
- ARM64 Windows：`arm64\sys_info.exe`
- 32 位 Windows：`i386\sys_info.exe`

发布包未签名。遇到 SmartScreen 提示时，请先核对 Release 中的 SHA-256。

## 与官方版的区别

- 提供简体中文界面，当前正在从运行时翻译迁移到原生 zh-CN 资源。
- 可执行文件和产品标识改为 `sys_info`。
- 不构建、不打包 KSystemInformer 内核驱动。

依赖驱动的功能会不可用，例如受保护进程的完整句柄枚举和部分内核堆栈功能。无驱动不等于反作弊白名单，运行受保护游戏时建议退出本程序。

## 当前验证范围

| 项目 | 当前状态 |
|---|---|
| 主程序静态对话框 | 106 个 en-US/zh-CN 同 ID 资源曾在历史 Windows x64 CI 中通过 PE 结构校验；当前本地新增提交尚未重新跑 Windows CI，人工界面验收仍未完成 |
| 动态文字 | PE Viewer、安装器和主程序分别已有 134、74、290 条使用原生 `STRINGTABLE`；DotNetTools、ExtendedServices、ExtendedTools、ToolStatus、UserNotes 分别已迁移 8、66、40、103、15 条，HardwareDevices、NetworkTools、OnlineChecks、Updater、WindowExplorer 合计迁移 47 条，合计 777 条。扩展审计到窗口文字、组合框（含普通字符串数组及结构体字段数组）及列表分组/项目和包装入口后，曾新增暴露的 57 条结构体数组组合框文字已经迁移，显示文字不再参与业务值解析；ExtendedServices 当前审计项已全部覆盖，主程序、DotNetTools、ExtendedTools、WindowExplorer 和 PE Viewer 又迁移 35 个无共享冲突的列表分组/项目，NetworkTools 的许可证提示、Ping、Tracert 和 WHOIS 动态窗口文字以及 HardwareDevices 的连接分组、网络状态和适配器详情分组/后备标题也已迁移，修正原生专用字典误覆盖旧运行时列表分组的审计假绿后，项目如实报告 580 条未翻译项。大量既有文字仍由兼容翻译层接管，不能据此宣称整体完成 |
| 生成器与源码契约 | 本地测试通过 |
| Windows x64 构建与原生加载 | 历史远端基线曾通过；当前本地分支新增内容尚未推送，不能宣称已通过 Windows 编译、启动或 UI 响应验证 |
| x86、ARM64、多 DPI 界面 | 尚未完成真实运行与视觉验收 |

这些检查不代表“全部界面 100% 汉化”，也不保证不存在崩溃或布局问题。发布状态以对应版本的 CI 和人工验收记录为准。

## 切换语言

关闭程序后，编辑便携目录中的 `sys_info.exe.settings.json`：

```json
{
  "Language": "en"
}
```

使用 `"zh-CN"` 恢复中文，重启后生效。

## 本地开发

```bash
python3 tools/zhcn/audit.py
python3 tools/zhcn/check_translation.py
python3 tools/zhcn/generate_translation.py --check
python3 tools/zhcn/generate_native_resources.py --check
python3 -m unittest discover -s tools/zhcn/tests -v
```

工具说明见 [tools/zhcn/README.md](tools/zhcn/README.md)。

## 已知限制

- 插件静态对话框资源已生成；插件动态文字的原生资源迁移尚未完成。
- 125%–200% DPI 下的字体清晰度、截断和重叠仍需 Windows 截图验收。
- 自动更新插件指向官方发布渠道，更新后可能恢复为官方英文版。
- 本项目与 System Informer 官方团队、游戏发行商及反作弊厂商无隶属关系。

## 许可证与上游

- 上游项目：[winsiderss/systeminformer](https://github.com/winsiderss/systeminformer)
- 许可证：[MIT](LICENSE.txt)
