# 进程详情选项卡字体修复实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让进程详情选项卡继承主界面的字体设置，并在 DPI 变化时安全更新字体句柄。

**架构：** 修复限定在 `procprp` 的新属性页宿主适配层。新增字体更新函数，使用现有 `PhCreateTreeWindowFont` 按窗口 DPI 创建字体，绑定到 `PhPropSheetNew` 的 Tab 控件，并由现有 `PH_PROCESS_PROPSHEETCONTEXT::PropSheetWindowFont` 持有和释放。

**技术栈：** C、Win32 GDI、PhTabNew、Python `unittest` 源码契约测试。

---

## 文件结构

- 创建：`tools/zhcn/tests/test_process_properties_tab_font_contract.py`，约束字体创建、绑定、DPI 更新和释放顺序。
- 修改：`SystemInformer/procprp.c`，实现进程详情选项卡专用字体生命周期。
- 修改：`docs/superpowers/plans/2026-09-08-process-properties-tab-font.md`，记录执行状态。

### 任务 1：建立失败的字体生命周期契约

**文件：**
- 创建：`tools/zhcn/tests/test_process_properties_tab_font_contract.py`

- [x] **步骤 1：编写失败的测试**

测试读取 `SystemInformer/procprp.c`，提取目标函数并断言以下行为：

```python
def test_tab_font_uses_tree_font_setting_and_rebinds_before_delete(self) -> None:
    body = compact(function_body(self.source, "PhpUpdateProcessPropTabFont"))
    self.assertIn("PhPropSheetNewGetTabControl(HostHandle)", body)
    self.assertIn("newFont = PhCreateTreeWindowFont(WindowDpi)", body)
    self.assertIn("if (!newFont) return;", body)
    self.assertLess(body.index("PropSheetContext->PropSheetWindowFont = newFont"), body.index("SetWindowFont(tabControlHandle, newFont, TRUE)"))
    self.assertLess(body.index("SetWindowFont(tabControlHandle, newFont, TRUE)"), body.index("DeleteFont(oldFont)"))

def test_initialization_dpi_refresh_and_cleanup_are_wired(self) -> None:
    initialized = compact(function_body(self.source, "PhpProcessPropertiesNewInitialized"))
    host = compact(function_body(self.source, "PhpProcessPropertiesNewHostWndProc"))
    self.assertIn("PhpUpdateProcessPropTabFont(propSheetContext, HostHandle, PhGetWindowDpi(HostHandle));", initialized)
    self.assertRegex(host, r"case WM_DPICHANGED:.*CallWindowProc\(oldWndProc.*PhpUpdateProcessPropTabFont\(propSheetContext, WindowHandle, LOWORD\(wParam\)\)")
    self.assertRegex(host, r"case WM_NCDESTROY:.*DeleteFont\(propSheetContext->PropSheetWindowFont\)")
```

- [x] **步骤 2：运行测试并确认红灯**

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.zhcn.tests.test_process_properties_tab_font_contract -v
```

预期：FAIL，原因是 `PhpUpdateProcessPropTabFont` 尚不存在，而不是测试语法或文件读取错误。

- [x] **步骤 3：提交红灯测试**

```bash
git add tools/zhcn/tests/test_process_properties_tab_font_contract.py docs/superpowers/plans/2026-09-08-process-properties-tab-font.md
git commit -m "test(ui): 约束进程详情选项卡字体生命周期"
```

### 任务 2：实现进程详情选项卡字体绑定

**文件：**
- 修改：`SystemInformer/procprp.c`
- 测试：`tools/zhcn/tests/test_process_properties_tab_font_contract.py`

- [x] **步骤 1：实现最少字体更新函数**

```c
static VOID PhpUpdateProcessPropTabFont(
    _Inout_ PPH_PROCESS_PROPSHEETCONTEXT PropSheetContext,
    _In_ HWND HostHandle,
    _In_ LONG WindowDpi
    )
{
    HWND tabControlHandle;
    HFONT newFont;
    HFONT oldFont;

    tabControlHandle = PhPropSheetNewGetTabControl(HostHandle);
    if (!tabControlHandle)
        return;

    newFont = PhCreateTreeWindowFont(WindowDpi);
    if (!newFont)
        return;

    oldFont = PropSheetContext->PropSheetWindowFont;
    PropSheetContext->PropSheetWindowFont = newFont;
    SetWindowFont(tabControlHandle, newFont, TRUE);

    if (oldFont)
        DeleteFont(oldFont);
}
```

- [x] **步骤 2：接入初始化、DPI 更新和销毁**

- `PhpProcessPropertiesNewInitialized` 创建宿主上下文后，使用 `PhGetWindowDpi(HostHandle)` 首次绑定字体。
- `WM_DPICHANGED` 先调用原宿主窗口过程完成 DPI 布局，再调用字体更新函数。
- `WM_NCDESTROY` 在释放 `propSheetContext` 前删除 `PropSheetWindowFont` 并清空字段。

- [x] **步骤 3：运行字体契约测试并确认绿灯**

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.zhcn.tests.test_process_properties_tab_font_contract tools.zhcn.tests.test_font_handle_contract tools.zhcn.tests.test_font_dpi_contract -v
```

预期：所有测试 PASS，退出码为 0。

- [ ] **步骤 4：提交最少实现**

```bash
git add SystemInformer/procprp.c tools/zhcn/tests/test_process_properties_tab_font_contract.py docs/superpowers/plans/2026-09-08-process-properties-tab-font.md
git commit -m "fix(ui): 修复进程详情选项卡字体过小"
```

### 任务 3：完整回归和 Windows 验证

**文件：**
- 修改：`docs/superpowers/plans/2026-09-08-process-properties-tab-font.md`

- [ ] **步骤 1：运行完整离线回归**

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/zhcn/tests -q
python3 tools/zhcn/audit.py
python3 tools/zhcn/check_translation.py --fail-on-untranslated
git diff --check
```

预期：测试、汉化审计和差异检查全部退出码为 0。

- [ ] **步骤 2：自审字体句柄生命周期**

确认新字体创建失败时保留旧字体；创建成功时先发布并绑定新字体，再删除旧字体；窗口销毁时仅删除进程详情窗口拥有的句柄。

- [ ] **步骤 3：推送并等待 GitHub Windows x64 CI**

```bash
git push origin zh-cn
gh run watch --exit-status
```

预期：Windows x64 构建、完整回归和启动冒烟全部通过。CI 不作为字体视觉清晰度证据。

- [ ] **步骤 4：记录实机验证边界**

请用户安装 CI 或 Release 产物，在原复现设备打开进程详情，并对比修复前后选项卡字号与清晰度。只有用户实机确认后，才能声明字体视觉问题已解决。
