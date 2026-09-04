# zh-CN 资源工具

这里放本地化数据、生成器和验证脚本。当前处于原生资源迁移期：主程序静态对话框使用生成的 zh-CN 资源，插件和动态文字暂时保留兼容翻译层。

## 常用命令

```bash
# 扫描英文源文件，生成临时清单
python3 tools/zhcn/audit.py

# 检查翻译键、占位符和未处理字符串
python3 tools/zhcn/check_translation.py

# 检查旧兼容字符串表是否与翻译数据一致
python3 tools/zhcn/generate_translation.py --check

# 检查主程序原生 zh-CN 对话框是否与英文资源同步
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
| `zh-CN.json` | 当前翻译数据源 |
| `generate_native_resources.py` | 生成 `SystemInformer/SystemInformer.zh-cn.rc` |
| `validate_templates.py` | 检查构建后 PE 中的 en-US/zh-CN 对话框、结构和字体 |
| `audit.py` | 只扫描英文源文件，不扫描生成的 `*.zh-cn.rc` |
| `check_translation.py` | 输出缺失键、无用键和占位符错误 |
| `generate_translation.py` | 生成过渡期运行时字典 |
| `tests/` | 源码和生成结果契约测试 |

`manifest.json` 与 `coverage-report.md` 是临时审计输出，不作为“覆盖率百分比”或发布质量证明。
