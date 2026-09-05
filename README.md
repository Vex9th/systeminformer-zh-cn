# System Informer 简体中文社区版

[![zh-ci](https://github.com/Vex9th/systeminformer-zh-cn/actions/workflows/zh-cn-build.yml/badge.svg?branch=zh-cn)](https://github.com/Vex9th/systeminformer-zh-cn/actions/workflows/zh-cn-build.yml)

System Informer 的非官方简体中文、无驱动便携版。程序名为 `sys_info.exe`，可与官方版并存。

汉化仍在完善中，不承诺“100% 汉化”；仍可能出现崩溃或界面布局问题。

## 下载与运行

从 [Releases](https://github.com/Vex9th/systeminformer-zh-cn/releases) 下载便携包，解压后运行：

- 64 位 Windows：`amd64\sys_info.exe`
- ARM64 Windows：`arm64\sys_info.exe`
- 32 位 Windows：`i386\sys_info.exe`

无需安装。发布包未签名；遇到 SmartScreen 提示时，请先核对 Release 中的 SHA-256。

## 重要说明

- 部分界面仍可能显示英文。
- 本项目不构建、不打包 KSystemInformer 内核驱动；依赖驱动的功能不可用。
- 无驱动不等于反作弊白名单。运行受保护游戏时，建议退出本程序。
- 自动更新插件指向官方发布渠道，更新后可能恢复为官方英文版。

例如，受保护进程的完整句柄枚举和部分内核堆栈功能需要驱动，因此本版本无法提供。

## 切换语言

关闭程序后，编辑便携目录中的 `sys_info.exe.settings.json`。只修改或添加 `Language` 字段，不要用下面的示例覆盖整个设置文件：

```json
{
  "Language": "en"
}
```

使用 `"zh-CN"` 恢复中文，重启后生效。

## 验证边界

发布工作流会在 Windows x64 上构建程序，并检查：`sys_info.exe` 能启动和响应、11 个插件 DLL 已载入、PE 中英文资源结构符合预期、发布包不含驱动。

这些检查不代表 11 个插件的功能均正常，也不代表全部文字、稳定性、崩溃路径或视觉效果已经验收。具体版本结果以对应 tag 的 CI 和 Release 说明为准。

macOS 本地只能执行源码、生成器和资源契约检查，不能运行或验证 Windows 的 `sys_info.exe`。

## 构建与贡献

- 汉化工具与检查命令：[tools/zhcn/README.md](tools/zhcn/README.md)
- Windows 构建流程：[zh-cn-build.yml](.github/workflows/zh-cn-build.yml)
- 上游构建说明：[System Informer build documentation](https://systeminformer.sourceforge.io/documentation.php)

## 已知限制

- 动态文字的原生资源迁移尚未完成，仍有旧兼容翻译逻辑。
- 尚未完成 Windows 多 DPI 的完整人工视觉验收；字体清晰度、文字截断、控件重叠和缩放问题仍可能存在。
- x86 和 ARM64 尚未完成与 x64 同等强度的真实运行验收。
- 本项目与 System Informer 官方团队、游戏发行商及反作弊厂商无隶属关系。

## 许可证与上游

- 上游项目：[winsiderss/systeminformer](https://github.com/winsiderss/systeminformer)
- 许可证：[MIT](LICENSE.txt)
