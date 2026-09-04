# zh-CN 本地化工具

本目录是简体中文社区版的字符串审计、翻译维护与校验工具。
翻译的唯一数据源是 `zh-CN.json`；编译进程序的字符串表由脚本生成并提交。

## 工作流

```bash
# 1. 重新扫描源码，生成字符串清单（派生数据，不提交）
python3 tools/zhcn/audit.py

# 2. 编辑 tools/zhcn/zh-CN.json 补充/修订翻译（遵循 glossary.md）

# 3. 校验：重复键、格式占位符一致性、未翻译项报告
python3 tools/zhcn/check_translation.py

# 4. 重新生成编译用字符串表（提交到 phlib/phtranslation_zhcn.c）
python3 tools/zhcn/generate_translation.py
```

CI 会在每次构建时重复 1、3、4（`--check` 模式），字符串表过期会导致构建失败。

## 文件说明

| 文件 | 作用 |
|---|---|
| `audit.py` | 扫描 `.rc` 与 C/C++ 源码中所有用户可见字符串，按运行时翻译插桩点分类 |
| `zh-CN.json` | 翻译数据源（英文原文 → 中文） |
| `check_translation.py` | 结构校验 + 审核报告（`coverage-report.md`） |
| `generate_translation.py` | 生成 `phlib/phtranslation_zhcn.c`（UTF-8 BOM，按 UTF-16 码元排序供 wcscmp 二分查找） |
| `glossary.md` | 术语表与风格约定 |
| `manifest.json` | 审计输出（派生数据，已 gitignore） |
| `coverage-report.md` | 变更清单与已审项目报告（派生数据，已 gitignore） |

## 运行时机制概述

所有翻译插桩点集中在 phlib 与少量主程序文件：菜单（PhEMenu）、列表列、
TreeNew 列、消息框/任务对话框、对话框模板（DLGTEMPLATE 翻译副本）、
状态栏与托盘通知。`zh-CN.json` 中不存在的键在运行时回退为英文原文，
因此上游更新引入的新字符串不会导致界面缺失，只会暂时显示英文。
