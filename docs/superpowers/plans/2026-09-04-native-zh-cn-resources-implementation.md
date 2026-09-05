# 原生中文资源实施计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框语法追踪进度。

**目标：** 按方案 B 将当前方案迁移到“模块内嵌 EN + zh-CN 资源”的本地化方式，去掉运行时重写文本层，降低崩溃与模糊风险。

**架构：** 在主程序、插件、工具各自的 `.rc` 中保持英文主资源，通过新增同 ID 的 `LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED` 资源块提供中文显示；运行时新增按语言获取资源的 helper，不再依赖英文原文查字典；动态文本统一改为 `IDS_*` 字符串表。

**技术栈：** C/C++、CMake/VcxProj、Windows 资源系统、Python（现有 `tools/zhcn` 脚本）

**当前状态：** 方案 B 尚未完成。主程序、11 个插件和独立工具的静态对话框以及语言感知加载路径已在源码落地；PE Viewer 的菜单、列表列名、选项和弹窗提示，安装器向导文字，以及主程序选项页提示已迁入原生字符串表。其余动态字符串、旧运行时翻译层移除、Windows CI、x86/ARM64 与多 DPI 验收仍按下列任务推进。

---

### 任务 1：建立迁移边界和验收基线

- 修改：`docs/superpowers/plans/2026-09-04-native-zh-cn-resources-implementation.md`
- 修改：`docs/superpowers/specs/2026-09-04-native-zh-cn-resources-design.md`

- [x] **步骤 1：确认要迁移的模块与可执行目标**

将以下模块列为第一阶段支持对象（并在说明里标注理由）：
- `SystemInformer`、`plugins/{UserNotes,ExtendedTools,ExtendedNotifications,DotNetTools,OnlineChecks,Updater,NetworkTools,HardwareDevices,WindowExplorer,ToolStatus,ExtendedServices}`、`tools/peview`、`tools/CustomSetupTool`、`tools/CustomSignTool`。

目标产出：一个可复用的模块列表（含资源文件路径 + RC 文件）供后续脚本/审计使用。

- [x] **步骤 2：建立初始资源契约清单**

命令：

```bash
cd /Users/r2/Developer/Sys_Info/systeminformer-zh-cn
rg --files -g '*.rc' | sort > docs/superpowers/plan-assets-rc-modules.txt
```

预期产出：文本列表文件，作为资源迁移台账起点。

---

### 任务 2：修复高优先级中文化运行时问题（过渡期安全阀）

- 修改：`phlib/phtranslation.c`
- 修改：`SystemInformer/runas.c`

- [x] **步骤 1：修复中文字体写入截断（当前模糊/裁切触发点）**

在 `PhTranslateDialogTemplateCopy()` 的字体写入处，将 `Microsoft YaHei UI` 按字符串长度写入，去掉固定字节写入长度导致的截断：

```c
static const WCHAR zhCnFont[] = L"Microsoft YaHei UI";
PhTlpWrite(&writer, (PVOID)zhCnFont, (wcslen(zhCnFont) + 1) * sizeof(WCHAR));
```

- [x] **步骤 2：修复 Run As 随机服务名拼接**

在 `PhExecuteRunAsCommand3()` 里改为：

```c
wcscpy_s(serviceName, ARRAYSIZE(serviceName), L"sys_info_");
PhGenerateRandomAlphaString(&serviceName[9], ARRAYSIZE(serviceName) - 9);
```

并保留 `RunAsOldServiceName` 的互斥缓存逻辑。

- [x] **步骤 3：本地静态审计这两处**

```bash
cd /Users/r2/Developer/Sys_Info/systeminformer-zh-cn
rg -n "PhTlpWrite\\(&writer, \\(PVOID\\)L\"Microsoft YaHei UI\"|PhGenerateRandomAlphaString\\(&serviceName|wcscpy_s\\(serviceName" phlib/SystemInformer SystemInformer/runas.c phlib/phtranslation.c
```

预期：仅命中新修正片段；无额外遗留旧逻辑。

- [x] **步骤 4：提交分支提交**

```bash
cd /Users/r2/Developer/Sys_Info/systeminformer-zh-cn
git add phlib/phtranslation.c SystemInformer/runas.c
git commit -m "fix: 修正中文字体写入截断与runas临时服务名"
```

---

### 任务 3：建立“禁用运行时翻译后”的主循环可回退路径（阶段一）

- 修改：`phlib/include/phtranslation.h`、`phlib/phtranslation.c`
- 修改：`SystemInformer/main.c`
- 修改：`phlib/guisup.c`

- [x] **步骤 1：保留接口但引入语言开关与回退**

先将 `PhTranslationEnabled` 的默认行为从“全局字典翻译”改为“兼容开关型”，并保证 `en` 与 `zh-CN` 均可稳定运行。

测试文件建议：`SystemInformer/main.c` 内新增一段日志或诊断输出，打印当前 `SETTING_LANGUAGE` 与 `PhTranslationEnabled` 决策是否一致。

- [x] **步骤 2：在 `main.c` 记录语言决策用于回归**

将当前语言配置读取代码段转为显式状态映射（仅在开发构建开启诊断时输出），后续可用于判断原生资源接管是否完全成功。

- [x] **步骤 3：保留构建通过**

运行：

```bash
cd /Users/r2/Developer/Sys_Info/systeminformer-zh-cn
python3 tools/zhcn/audit.py
python3 tools/zhcn/check_translation.py
python3 tools/zhcn/generate_translation.py --check
```

预期：脚本全部成功（若当前资源与字典不一致仍按回退路径记录，而不是构建中断）。

- [x] **步骤 4：提交**

```bash
git add phlib/include/phtranslation.h phlib/phtranslation.c SystemInformer/main.c phlib/guisup.c
git commit -m "feat(i18n): 引入语言决策与翻译层回退断点"
```

---

### 任务 4：开始原生资源落地（主程序）

- 修改：`SystemInformer/SystemInformer.rc`
- 修改：`SystemInformer/SystemInformer.zh-cn.rc`（新增）
- 修改：`phlib/include/mapldr.h` / `phlib/mapldr.c`（如需语言参数化）

- [x] **步骤 1：抽出主程序静态对话框英文资源的 zh-CN 复本**

在新增 `SystemInformer/SystemInformer.zh-cn.rc` 中加入：

```rc
LANGUAGE LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED
```

当前主程序 `.rc` 没有 `MENU` 或 `STRINGTABLE` 块；先复制全部对话框 ID 并逐条替换文案。动态菜单和 C 代码字符串继续走英文回退兼容层，后续迁移到 `IDS_*`。

- [x] **步骤 2：构建资源可达性校验**

```bash
cd /Users/r2/Developer/Sys_Info/systeminformer-zh-cn
python3 tools/zhcn/audit.py
python3 tools/zhcn/validate_templates.py bin/Release64/sys_info.exe
```

预期：可见模板与字符串 ID 与英文版保持一一映射（控件 ID/文本 ID 不缺失）。

历史验证记录（2026-09-05）：[Windows CI 33898026678](https://github.com/Vex9th/systeminformer-zh-cn/actions/runs/33898026678) 曾通过；该次构建后 PE 包含 en-US 106 个、zh-CN 106 个对话框，结构失败 0，并完成当时版本的原生资源加载探针、11 个插件加载和主界面响应冒烟测试。此记录不代表其后的本地提交已经通过 Windows 验证。

- [x] **步骤 3：提交**

```bash
git add SystemInformer/SystemInformer.rc SystemInformer/SystemInformer.zh-cn.rc
git commit -m "i18n(main): 增加主程序 zh-CN 资源容器"
```

---

### 任务 5：README 与 release 声明从“覆盖率百分比神话”切到分层验证

- 修改：`README.md`
- 修改：`tools/zhcn/README.md`
- 修改：`.github/workflows/zh-cn-build.yml`
- 修改：`docs/superpowers/specs/2026-09-04-native-zh-cn-resources-design.md`

- [x] **步骤 1：移除 100%/百分比导向结论**

将覆盖率字段替换为：已覆盖模块、未覆盖路径、人工验证状态、运行测试类型。

- [x] **步骤 2：CI 产物只上报可验证层级**

生成发布说明时不再写“翻译覆盖率 100%”，改为结构校验通过率 + 运行 smoke 通过率 + 视觉验收通过率。

- [x] **步骤 3：提交**

```bash
git add README.md tools/zhcn/README.md .github/workflows/zh-cn-build.yml docs/superpowers/specs/2026-09-04-native-zh-cn-resources-design.md
git commit -m "docs(i18n): 收敛中文化宣告口径，去除覆盖率百分比表述"
```

---

### 任务 6：迁移 11 个插件的静态对话框资源

- 修改：`plugins/*/*.vcxproj`、`plugins/*/*.vcxproj.filters`
- 新增：`plugins/*/*.zh-cn.rc`
- 修改：`tools/zhcn/generate_native_resources.py`
- 修改：`tools/zhcn/validate_templates.py`
- 修改：`.github/workflows/zh-cn-build.yml`

- [x] **步骤 1：生成并接入插件 zh-CN 对话框资源**

11 个插件共 107 个对话框。每个 DLL 保留 en-US 资源，并编译同 ID 的 zh-CN 资源；中文模板使用完整的 `Microsoft YaHei UI` 字体名。

- [x] **步骤 2：建立源码与工程接入契约测试**

检查模块数、对话框 ID、字体、UTF-8 BOM、`.vcxproj` 和 `.vcxproj.filters` 接入。生成器 `--check` 必须同时检查主程序和全部插件。

- [x] **步骤 3：让 PE 校验器接受多个构建目标**

CI 明确传入 `sys_info.exe` 和 11 个插件 DLL，逐文件比较 en-US 与 zh-CN 对话框结构。不能用“插件已加载”替代资源内容校验。

- [ ] **步骤 4：在 Windows CI 编译并校验全部插件 DLL**

只有 GitHub Windows runner 的编译和 PE 校验成功后，才把本任务标为完成。本地 macOS 测试不作为 Windows 构建证据。

---

### 任务 7：迁移独立工具静态资源

- 修改：`tools/peview/peview.rc`、`tools/CustomSetupTool/resource.rc`、`tools/CustomSignTool/resource.rc`
- 修改：对应 `.vcxproj` 和 `.vcxproj.filters`
- 修改：资源生成器、契约测试与 PE 校验目标

- [x] **步骤 1：盘点每个工具的可见资源和实际发布范围**

`peview` 有 47 个静态对话框，`CustomSetupTool` 有 10 个。`CustomSignTool` 只有中立语言 manifest，没有 `DIALOG`、`MENU` 或 `STRINGTABLE`；契约测试负责在它以后新增可见资源时失败。

- [x] **步骤 2：生成并接入同 ID 的 zh-CN 资源**

生成器当前覆盖 14 个实际存在可见对话框的资源宿主，共 270 个对话框；本地生成一致性、工程 XML 与资源 ID 契约已通过。

- [ ] **步骤 3：在 Windows CI 验证构建产物中的双语资源**

---

### 任务 8：将动态 UI 文案迁移到 `STRINGTABLE`

- 新增：动态 UI 字面量守卫及带理由的精确白名单
- 修改：主程序、插件和工具的 `resource.h`、`.rc` 与 UI 调用点

- [x] **步骤 1：扫描并分类所有 UI 输出入口**
- [ ] **步骤 2：按模块建立稳定的 `IDS_*` 资源 ID**
- [ ] **步骤 3：将直接英文宽字符串改为模块内 `PhLoadString` 加载**
- [ ] **步骤 4：校验 en-US/zh-CN 字符串表 ID 和格式占位符一致**
- [ ] **步骤 5：让新增未迁移 UI 英文字面量在 CI 中失败**

进行中（2026-09-05）：审计范围已覆盖主程序、插件、`peview`、`CustomSetupTool` 和 `CustomSignTool`。当前共 301 条 en-US/zh-CN `STRINGTABLE` 项：PE Viewer 128 条，安装器 74 条，主程序 97 条，ExtendedServices 和 UserNotes 各 1 条；PE Viewer 的菜单、列表列名、选项和弹窗提示，以及主程序选项/启动/公共错误提示已迁移，并新增扫描式守卫防止英文提示回流。审计现已修正消息宏参数位置，排除注释死代码，并按 C 编译语义合并相邻字符串、检查格式化后续参数和未解析变量；旧字典无法可靠接管的后续参数已迁移调用点，早期崩溃提示保留不依赖缓存的静态后备。当前仍有 139 条已识别动态提示未作翻译决定，PE Viewer 其余动态字段、主程序其余动态文字和插件动态文字仍使用旧兼容字典，因此任务 8 仍不能勾选完成。

---

### 任务 9：移除旧运行时翻译层和百分比链路

- 删除：英文原文到中文的运行时字典、模板重写及对应生成代码
- 修改：旧审计、同步、构建和发布流程

- [ ] **步骤 1：确认静态资源和动态字符串已全部接管**
- [ ] **步骤 2：删除 `phtranslation` 字典查找与模板改写路径**
- [ ] **步骤 3：删除覆盖率报告、自动翻译和失效的旧校验入口**
- [ ] **步骤 4：验证环境变量 `Path` 等用户数据不再进入翻译路径**

---

### 任务 10：完成运行、架构和视觉验收

- 修改：Windows 运行测试、CI 验收矩阵和验证文档

- [ ] **步骤 1：覆盖 Options、属性页、Run As 和代表性插件页面的反复开关**
- [ ] **步骤 2：验证正常退出、异常退出、超时和崩溃转储收集**
- [ ] **步骤 3：完成 x64 与 x86 的真实运行测试**
- [ ] **步骤 4：分别记录 ARM64 构建与 ARM64 真机运行状态**
- [ ] **步骤 5：完成 Windows 10/11、100%/150%/200% DPI 的截图与人工视觉签核**
- [ ] **步骤 6：确认 README 和发布说明只陈述本次真实证据**

任务 6 至任务 10 全部完成前，不创建方案 B 正式 Release，也不宣称“整体完成”。

---

### 自检

1. 设计文档里的每一章节都对应至少一项任务？  
2. 任何“待定/后续处理”字符串都已替换为实操步骤？  
3. 任务 2 的 hotfix 是否已经可独立测试通过且不引入额外 ABI/API 变更？  
4. 任务 4/5 是否为方案 B 的第二阶段迁移做了清晰的模块/验收切换点？

计划保存在 `docs/superpowers/plans/2026-09-04-native-zh-cn-resources-implementation.md`，并随每个可验证批次更新完成状态。
