# zh-CN 资源工具

这里放汉化数据、生成器和验证脚本。项目仍处于原生资源与旧兼容翻译层并存阶段。

审计器只统计它能够识别的入口，并保守追踪一层局部文字变量；扫描结果不是界面覆盖率，也不能证明 Windows 实际运行、稳定性或视觉效果。

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

## 数据流

- `zh-CN.json` 是翻译数据源；`strings` 供过渡期运行时字典使用，`native_strings` 只供原生资源使用。
- `audit.py` 生成临时的 `manifest.json`，`check_translation.py` 再生成 `coverage-report.md`。
- `generate_native_resources.py` 生成各资源宿主的 `*.zh-cn.rc`。
- `validate_templates.py` 检查构建后 PE 的资源结构、ID、占位符和字体元数据。

`manifest.json` 和 `coverage-report.md` 只列出扫描器当前识别到的工程库存。PE 结构检查也不检查真实字体渲染、文字截断或控件重叠；macOS 本地检查不能替代 Windows 的 RC/MSVC 构建、启动和 UI 验收。
