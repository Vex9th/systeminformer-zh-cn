# zh-CN 本地化工具

负责三件事：扫描新英文文本、维护 `zh-CN.json`、生成可编译字符串表。

```bash
# 1) 生成清单（不提交）
python3 tools/zhcn/audit.py

# 2) 校验字符串完整性与一致性
python3 tools/zhcn/check_translation.py

# 3) 生成编译用字符串表（提交 phlib/phtranslation_zhcn.c）
python3 tools/zhcn/generate_translation.py
```

CI 每次构建都会执行 1 和 3 的 `--check` 校验；输出结果不一致会阻断构建。

## 文件说明

| 文件 | 作用 |
|---|---|
| `audit.py` | 扫描 `.rc` 与 C/C++ 源码中所有用户可见字符串，按运行时翻译插桩点分类 |
| `zh-CN.json` | 翻译数据源（英文原文 → 中文） |
| `check_translation.py` | 结构校验 + 变更审计报告（`coverage-report.md`） |
| `generate_translation.py` | 生成 `phlib/phtranslation_zhcn.c`（UTF-8 BOM，按 UTF-16 码元排序供 wcscmp 二分查找） |
| `glossary.md` | 术语表与风格约定 |
| `manifest.json` | 审计输出（派生数据，已 gitignore） |
| `coverage-report.md` | 变更清单与审计结果（派生数据，已 gitignore） |

## 运行时机制概述

所有翻译插桩点集中在 phlib 与少量主程序文件：菜单（PhEMenu）、列表列、
TreeNew 列、消息框/任务对话框、对话框模板（DLGTEMPLATE 翻译副本）、
状态栏与托盘通知。`zh-CN.json` 中不存在的键在运行时回退为英文原文，
因此上游更新引入的新字符串不会导致界面缺失，只会暂时显示英文。
