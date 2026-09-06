# System Informer 简体中文社区版

System Informer 的非官方简体中文、无驱动便携版。程序名为 `sys_info.exe`，可与官方版并存。当前仍在开发，不是“100% 汉化”或“全部测试通过”的成品。

## 下载与运行

从 [Releases](https://github.com/Vex9th/systeminformer-zh-cn/releases) 下载便携包，解压后运行：

- 64 位 Windows：`amd64\sys_info.exe`
- ARM64 Windows：`arm64\sys_info.exe`
- 32 位 Windows：`i386\sys_info.exe`

无需安装。发布包未签名；遇到 SmartScreen 提示时，请先核对 Release 中公布的 SHA-256。

## 必须知道

- 部分界面仍有英文，也可能出现崩溃、字体模糊、文字截断或控件重叠。
- 本项目不构建、不打包 KSystemInformer 内核驱动；依赖驱动的功能不可用。
- 本项目不构建、不加载、不打包自动更新插件；新版本需手动下载。
- 无驱动不等于反作弊白名单。运行受保护游戏时，建议退出本程序。
- 当前开发设备是 macOS，尚不能确认本地改动在 Windows 上的启动、UI 和插件表现。

## 切换语言

关闭程序后，编辑便携目录中的 `sys_info.exe.settings.json`，只修改或添加 `Language` 字段：

```json
{
  "Language": "en"
}
```

使用 `"zh-CN"` 恢复中文。不要用示例覆盖整个设置文件，修改后重启程序。

## 开发与验证

macOS 本地只能检查源码、生成结果和资源契约：

```bash
python3 tools/zhcn/generate_translation.py --check
python3 tools/zhcn/generate_native_resources.py --check
python3 -m unittest discover -s tools/zhcn/tests -v
git diff --check
```

这些命令不能证明 Windows 可执行文件、UI、字体或插件正常。Windows 构建和冒烟测试见 [zh-cn-build 工作流](.github/workflows/zh-cn-build.yml)；只有对应提交的 CI 或实机记录实际通过，才能写成“已验证”。

## 相关链接

- [汉化工具说明](tools/zhcn/README.md)
- [上游项目](https://github.com/winsiderss/systeminformer) 与 [上游构建说明](https://systeminformer.sourceforge.io/documentation.php)
- [MIT 许可证](LICENSE.txt)

本项目与 System Informer 官方团队、游戏发行商及反作弊厂商无隶属关系。
