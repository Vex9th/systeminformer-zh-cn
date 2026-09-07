# 2026-09-07 上游同步实施计划

> **面向 AI 代理的工作者：** 使用 superpowers:executing-plans 逐项执行。所有上游新增可见英文必须迁入模块原生资源，不能恢复运行时翻译字典。

**目标：** 将 `upstream/master` 的 16 个提交合入方案 B，保留上游功能并补齐原生简体中文资源，验证后合回 `zh-cn`、推送并运行 Release。

**架构：** 以上游实现为功能真源，以当前方案 B 的 `IDS_*` 和语言感知资源加载为显示真源。冲突解决必须同时保留上游新增参数、状态与数据结构，以及当前资源 getter 和英文 fallback；不得用裸英文或恢复 `PhTranslateString` 绕过审计。

**技术栈：** C/C++、Windows RC、Python `tools/zhcn` 审计与生成器、GitHub Actions

---

### 任务 1：建立隔离基线并合并上游

**文件：**
- 修改：本次上游涉及的 SystemInformer、phlib、插件和工具源文件

- [x] **步骤 1：在隔离工作树运行合并前完整回归**

运行：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/zhcn/tests -q`

预期：698 项通过，0 失败。

- [x] **步骤 2：合并 `upstream/master` 并记录实际冲突集合**

运行：`git merge --no-ff upstream/master`

预期：出现已预演的中文资源调用点冲突；不得使用整文件 `ours` 或 `theirs`。

### 任务 2：保留搜索与设置功能并维持原生资源边界

**文件：**
- 修改：`SystemInformer/{chcol,envdlg,findobj,informerwnd,main,memsrcht,options,prpgenv,prpghndl,prpgmem,prpgmod,prpgthrd,prpgwmi,runaspkg,thrdstks,usrlist}.c`
- 修改：`SystemInformer/include/{phapp,phsettings}.h`
- 修改：`SystemInformer/resources/settings.schema.json`
- 修改：`SystemInformer/settings.c`

- [x] **步骤 1：保留上游 `PhCreateSearchControl2` 与每个搜索框独立设置键**

每个冲突调用保留当前 `PhGetApplicationUiString(IDS_*)` banner，同时加入上游新增的 regex/case-sensitive setting 参数。

- [x] **步骤 2：保留设置文件损坏检测和异步环境变量窗口行为**

按上游状态变量和生命周期合并，保留当前中文错误文字资源 getter。

- [x] **步骤 3：运行搜索框、设置与窗口资源定向测试**

运行：`python3 -m unittest -q tools.zhcn.tests.test_remaining_direct_window_and_tab_resources tools.zhcn.tests.test_phlib_runtime_native_resources tools.zhcn.tests.test_runtime_translation_layer_retired`

预期：全部通过。

### 任务 3：迁移 ExtendedTools 命名管道新界面

**文件：**
- 修改：`plugins/ExtendedTools/{ExtendedTools.rc,ExtendedTools.zh-cn.rc,exttools.h,main.c,namedpipes.c,resource.h}`
- 修改：`tools/zhcn/zh-CN.json`
- 修改：与 ExtendedTools 资源契约相关的测试

- [x] **步骤 1：采用上游 TreeNew、搜索和复制实现**

保留上游列模型、排序、搜索、复制、句柄/目录两种枚举路径和设置持久化。

- [x] **步骤 2：为所有新增列名、状态、菜单和搜索提示建立稳定资源 ID**

英文和 zh-CN `STRINGTABLE` 必须同 ID、同占位符；调用点通过 `EtGetUiString` 获取并保留英文 fallback。

- [x] **步骤 3：先让审计/契约测试暴露新增裸英文，再生成资源并验证转绿**

运行：`python3 tools/zhcn/audit.py && python3 tools/zhcn/check_translation.py --fail-on-untranslated`

预期：迁移前失败；完成资源路由后未翻译 0。

### 任务 4：同步其余上游资源与安全修复

**文件：**
- 修改：`SystemInformer/SystemInformer.rc` 及 zh-CN 资源
- 修改：`plugins/NetworkTools/{ping,whois}.c`
- 修改：`tools/peview/{peview,peview.zh-cn}.rc`
- 修改：`tools/peview/settings.c`
- 修改：生成器数据和资源契约测试

- [x] **步骤 1：保留 Ping、Whois、Run As、菜单泄漏和主题修复**

这些纯行为修复按上游语义合入，不改变方案 B 的资源加载边界。

- [x] **步骤 2：同步英文 RC 结构并重新生成 zh-CN 资源**

运行：`python3 tools/zhcn/generate_native_resources.py`

- [x] **步骤 3：验证资源和扫描清单**

运行：`python3 tools/zhcn/generate_native_resources.py --check && python3 tools/zhcn/audit.py && python3 tools/zhcn/check_translation.py --fail-on-untranslated`

预期：14 个宿主一致，未翻译 0，placeholder error 0。

### 任务 5：回归、审查、集成和发布

**文件：**
- 修改：`docs/superpowers/plans/2026-09-07-upstream-sync.md`

- [x] **步骤 1：运行完整离线回归和差异检查**

运行：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/zhcn/tests -q && git diff --check`

- [x] **步骤 2：只读代码审查并修复全部 P0/P1**

重点审查上游功能完整性、资源所有权、设置迁移、TreeNew 生命周期及审计 fail-closed 行为。

- [x] **步骤 3：提交隔离同步分支并合回 `zh-cn`**

合回前确认主工作树仍只保留用户的 `SystemInformer/SystemInformer.def.h`，不将其暂存或覆盖。

- [ ] **步骤 4：推送 `zh-cn` 并等待 GitHub Windows CI 结束**

CI 未通过不得运行 Release；失败时读取真实日志并修复根因。

- [ ] **步骤 5：沿用仓库现有 tag/version 规则运行 Release**

发布说明必须准确区分自动冒烟与未完成的视觉、多 DPI、x86/ARM64 真机验收。
