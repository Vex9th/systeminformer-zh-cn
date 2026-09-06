#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCES = (
    ("IDS_PH_BUTTON_CONTINUE", 2710, "Continue", "继续"),
    ("IDS_PH_ELEVATION_PERMISSION_CONTENT", 2711, "You will need to provide administrator permission. Click Continue to complete this operation.", "你需要提供管理员权限。单击“继续”完成此操作。"),
    ("IDS_PH_DEBUGGER_WINDBG_COMMAND", 2712, "WinDbg\\nGraphical debugger for both user-mode and kernel-mode debugging.", "WinDbg\\n用于用户模式和内核模式调试的图形化调试器。"),
    ("IDS_PH_DEBUGGER_WINDBG_PREVIEW_COMMAND", 2713, "WinDbg (Preview)\\nModern graphical debugger for both user-mode and kernel-mode debugging.", "WinDbg (Preview)\\n支持用户模式和内核模式调试的现代图形化调试器。"),
    ("IDS_PH_DEBUGGER_CDB_COMMAND", 2714, "CDB\\nCommand-line debugger for user-mode applications.", "CDB\\n用于用户模式应用程序的命令行调试器。"),
    ("IDS_PH_DEBUGGER_KD_COMMAND", 2715, "KD\\nKernel debugger for low-level system debugging.", "KD\\n用于底层系统调试的内核调试器。"),
    ("IDS_PH_DEBUGGER_NTSD_COMMAND", 2716, "NTSD\\nLegacy command-line debugger similar to CDB.", "NTSD\\n与 CDB 类似的旧版命令行调试器。"),
    ("IDS_PH_DEBUGGER_SYSTEM_DEFAULT_FORMAT", 2717, "(System Default)\\n%s", "（系统默认）\\n%s"),
    ("IDS_PH_DEBUGGER_SYSTEM_DEFAULT_UNCONFIGURED", 2718, "System Default\\nNo debugger configured in AeDebug registry key.", "系统默认\\nAeDebug 注册表项中未配置调试器。"),
    ("IDS_PH_DEBUGGER_SELECT_INSTRUCTION", 2719, "Select a system debugger to use for this process:", "选择要用于此进程的系统调试器："),
    ("IDS_PH_DEBUGGER_SELECT_CONTENT", 2720, "You can choose from the installed debugging tools below.", "你可以从下方已安装的调试工具中进行选择。"),
    ("IDS_PH_ACTIVITY_MODERATION_SYSTEM_MANAGED", 2721, "System managed", "系统管理"),
    ("IDS_PH_ACTIVITY_MODERATION_ALLOW", 2722, "Allow activity moderation throttling", "允许活动调节节流"),
    ("IDS_PH_ACTIVITY_MODERATION_DISABLE", 2723, "Disable activity moderation throttling", "禁用活动调节节流"),
    ("IDS_PH_SAVE", 2724, "Save", "保存"),
    ("IDS_PH_ACTIVITY_MODERATION_INSTRUCTION", 2725, "Select the process activity moderation throttling state.", "选择进程活动调节的节流状态。"),
    ("IDS_PH_ACTIVITY_MODERATION_DETAILS_FORMAT", 2726, "System-managed activity moderation settings are automatically removed by Windows when the executable is deleted or was last executed more than 7 days ago.\\r\\n\\r\\nImage: %s\\r\\nUpdated: %s", "当可执行文件被删除，或距上次执行超过 7 天时，Windows 会自动删除由系统管理的活动调节设置。\\r\\n\\r\\n映像：%s\\r\\n更新时间：%s"),
    ("IDS_PH_RELATIVE_AND_ABSOLUTE_TIME_FORMAT", 2727, "%s ago (%s)", "%s 前（%s）"),
    ("IDS_PH_CRASH_DUMP_FULL_BUTTON", 2728, "Full\\nA complete dump of the process, rarely needed most of the time.", "完整\\n进程的完整转储，通常很少需要。"),
    ("IDS_PH_CRASH_DUMP_NORMAL_BUTTON", 2729, "Normal\\nFor most purposes, this dump file is the most useful.", "普通\\n适用于大多数情况，也是最实用的转储文件。"),
    ("IDS_PH_CRASH_DUMP_MINIMAL_BUTTON", 2730, "Minimal\\nA very limited dump with limited data.", "最小\\n仅包含非常有限的数据。"),
    ("IDS_PH_CRASH_RESTART_BUTTON", 2731, "Restart\\nRestart the application.", "重启\\n重新启动应用程序。"),
    ("IDS_PH_CRASH_IGNORE_BUTTON", 2732, "Ignore", "忽略"),
    ("IDS_PH_CRASH_EXIT_BUTTON", 2733, "Exit", "退出"),
    ("IDS_PH_CRASH_TITLE", 2734, "System Informer has crashed :(", "sys_info 已崩溃 :("),
    ("IDS_PH_CRASH_MINIDUMP_PROMPT", 2735, "System Informer has crashed :(\\r\\n\\r\\nDo you want to create a minidump on the Desktop?", "sys_info 已崩溃 :(\\r\\n\\r\\n要在桌面上创建小型转储吗？"),
    ("IDS_PH_KSI_INITIALIZING_DRIVER", 2736, "Initializing System Informer kernel driver...", "正在初始化 sys_info 内核驱动程序..."),
    ("IDS_PH_KSI_INITIAL_ELAPSED", 2737, "0 ms...", "0 ms..."),
    ("IDS_PH_KSI_SUPPORT_PENDING_TITLE", 2738, "Platform support pending review.", "平台支持待审核。"),
    ("IDS_PH_KSI_SUPPORT_PENDING_CONTENT", 2739, "Your kernel version is pending review on the development branch. Your kernel will be supported in the next build!", "你的内核版本正在开发分支中等待审核，将在下一个版本中获得支持！"),
    ("IDS_PH_KSI_UNSUPPORTED_TITLE", 2740, "Kernel version not supported", "不支持该内核版本"),
    ("IDS_PH_KSI_UNSUPPORTED_CANARY_CONTENT", 2741, "This kernel version is not yet supported. Your kernel version is pending review on the development branch.", "此内核版本尚不受支持。你的内核版本正在开发分支中等待审核。"),
    ("IDS_PH_KSI_UNSUPPORTED_STABLE_CONTENT", 2742, "This kernel version is not yet supported. For the latest kernel support switch to the Canary update channel (Help > Check for updates > Canary > Check).", "此内核版本尚不受支持。要获得最新内核支持，请切换到 Canary 更新通道（帮助 > 检查更新 > Canary > 检查）。"),
    ("IDS_PH_KSI_CHECKING_PLATFORM_UPDATE", 2743, "Checking for pending platform update...", "正在检查待处理的平台更新..."),
    ("IDS_PH_THREAD_STACK_PROCESSING_FRAMES", 2744, "Processing stack frames...", "正在处理堆栈帧..."),
    ("IDS_PH_THREAD_STACK_LOADING_SYMBOLS", 2745, "Loading symbols...", "正在加载符号..."),
    ("IDS_PH_THREAD_STACK_LOADING_IMAGE_SYMBOLS", 2746, "Loading symbols for image...", "正在加载映像符号..."),
    ("IDS_PH_SERVICE_PASSWORD_PLACEHOLDER", 2747, "password", "密码"),
    ("IDS_PH_THREAD_STACK_PROCESSING_FRAME_FORMAT", 2748, "Processing stack frame #%lu...", "正在处理堆栈帧 #%lu..."),
)

SOURCE_FILES = ("actions.c", "main.c", "ksisup.c", "thrdstk.c", "srvprp.c")
TARGET_LITERALS = tuple(row[2].replace("\\r", "\r").replace("\\n", "\n") for row in RESOURCES)
EARLY_CRASH_FALLBACKS = tuple(
    row[2].replace("\\r", "\r").replace("\\n", "\n")
    for row in RESOURCES
    if row[0].startswith("IDS_PH_CRASH_")
)
LEGACY_DEBUGGER_LITERALS = (
    "🪟 WinDbg\nGraphical debugger for both user-mode and kernel-mode debugging.",
    "🪟 WinDbg (Preview)\nModern graphical debugger for both user-mode and kernel-mode debugging.",
    "📺 CDB\nCommand-line debugger for user-mode applications.",
    "📺 KD\nKernel debugger for low-level system debugging.",
    "📺 NTSD\nLegacy command-line debugger similar to CDB.",
    "⚙ (System Default)\n%s",
    "⚙ System Default\nNo debugger configured in AeDebug registry key.",
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("main_dialog_native_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$', text
        )
    }


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"function not found: {name}")
    opening = source.find("{", match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated function: {name}")


class SystemInformerDialogNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: (APP_ROOT / name).read_text(encoding="utf-8-sig")
            for name in SOURCE_FILES
        }

    def test_resource_tail_and_bilingual_values_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in RESOURCES:
            with self.subTest(symbol=symbol):
                self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
                self.assertEqual(english.get(symbol), en)
                self.assertEqual(chinese.get(symbol), zh)

        self.assertEqual([row[1] for row in RESOURCES], list(range(2710, 2749)))
        self.assertEqual(len(english), 957)
        self.assertEqual(len(chinese), 957)
        self.assertRegex(header, r"(?m)^#define\s+IDS_PH_LAST\s+IDS_PH_CONFIRM_USER_OBJECT$")
        self.assertRegex(header, r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2957$")

    def test_actions_taskdialogs_use_native_resources_and_existing_shared_ids(self) -> None:
        source = self.audit.mask_c_comments(self.sources["actions.c"])
        elevate = function_body(source, "PhpShowElevatePrompt")
        debugger = function_body(source, "PhUiDebugProcess")
        moderation = function_body(source, "PhUiSetActivityModeration")

        self.assertIn("{ IDYES, PhGetApplicationUiString(IDS_PH_BUTTON_CONTINUE) }", elevate)
        self.assertIn("config.pszContent = PhGetApplicationUiString(IDS_PH_ELEVATION_PERMISSION_CONTENT);", elevate)

        for resource in (
            "IDS_PH_DEBUGGER_WINDBG_COMMAND", "IDS_PH_DEBUGGER_WINDBG_PREVIEW_COMMAND",
            "IDS_PH_DEBUGGER_CDB_COMMAND", "IDS_PH_DEBUGGER_KD_COMMAND",
            "IDS_PH_DEBUGGER_NTSD_COMMAND", "IDS_PH_DEBUGGER_SYSTEM_DEFAULT_UNCONFIGURED",
        ):
            self.assertIn(f"PhGetApplicationUiString({resource})", debugger)
        for variable, icon, resource in (
            ("windbgButtonText", r"\\U0001FA9F", "IDS_PH_DEBUGGER_WINDBG_COMMAND"),
            ("windbgPreviewButtonText", r"\\U0001FA9F", "IDS_PH_DEBUGGER_WINDBG_PREVIEW_COMMAND"),
            ("cdbButtonText", r"\\U0001F4FA", "IDS_PH_DEBUGGER_CDB_COMMAND"),
            ("kdButtonText", r"\\U0001F4FA", "IDS_PH_DEBUGGER_KD_COMMAND"),
            ("ntsdButtonText", r"\\U0001F4FA", "IDS_PH_DEBUGGER_NTSD_COMMAND"),
        ):
            self.assertRegex(
                debugger,
                rf"{variable}\s*=\s*PhConcatStrings2\(L\"{icon} \",\s*PhGetApplicationUiString\({resource}\)\)",
            )
            self.assertEqual(debugger.count(f"PhClearReference(&{variable});"), 1)
        self.assertRegex(
            debugger,
            r"PhFormatString\(\s*PhGetApplicationUiString\(IDS_PH_DEBUGGER_SYSTEM_DEFAULT_FORMAT\),\s*registryDebuggerName->Buffer",
        )
        self.assertIn('PhConcatStrings2(L"\\u2699 ",', debugger)
        self.assertIn("config.pszMainInstruction = PhGetApplicationUiString(IDS_PH_DEBUGGER_SELECT_INSTRUCTION);", debugger)
        self.assertIn("config.pszContent = PhGetApplicationUiString(IDS_PH_DEBUGGER_SELECT_CONTENT);", debugger)

        for resource in (
            "IDS_PH_ACTIVITY_MODERATION_SYSTEM_MANAGED", "IDS_PH_ACTIVITY_MODERATION_ALLOW",
            "IDS_PH_ACTIVITY_MODERATION_DISABLE", "IDS_PH_SAVE", "IDS_PH_CANCEL",
            "IDS_PH_ACTIVITY_MODERATION_INSTRUCTION", "IDS_PH_ACTIVITY_MODERATION_DETAILS_FORMAT",
            "IDS_PH_RELATIVE_AND_ABSOLUTE_TIME_FORMAT", "IDS_PH_NOT_AVAILABLE",
        ):
            self.assertIn(f"PhGetApplicationUiString({resource})", moderation)
        self.assertRegex(
            moderation,
            r"PhaFormatString\(PhGetApplicationUiString\(IDS_PH_RELATIVE_AND_ABSOLUTE_TIME_FORMAT\),\s*PhGetString\(startTimeRelativeString\),\s*PhGetString\(startTimeString\)\)",
        )

    def test_crash_dialog_uses_stable_application_resources_without_auto_pool(self) -> None:
        main = self.audit.mask_c_comments(self.sources["main.c"])
        crash = function_body(main, "PhpUnhandledExceptionCallback")
        header = (APP_ROOT / "include" / "phapp.h").read_text(encoding="utf-8-sig")
        self.assertIn(
            "return PhGetStringOrEmpty(PhApplicationUiStrings[ResourceId - IDS_PH_FIRST]);",
            main,
        )
        self.assertRegex(main, r"PCWSTR\s+PhGetApplicationUiStringOrDefault\(")
        self.assertIn("PhGetApplicationUiStringOrDefault(", header)
        self.assertIn(
            "return PhGetStringOrDefault(\n"
            "        PhApplicationUiStrings[ResourceId - IDS_PH_FIRST],\n"
            "        DefaultString",
            main,
        )
        helper = function_body(main, "PhGetApplicationUiStringOrDefault")
        self.assertNotIn("assert(", helper)
        button_routes = ((101, "FULL"), (102, "NORMAL"), (103, "MINIMAL"), (104, "RESTART"), (105, "IGNORE"), (106, "EXIT"))
        for button_id, suffix in button_routes:
            self.assertRegex(
                crash,
                rf"\{{\s*{button_id},\s*PhGetApplicationUiStringOrDefault\(\s*"
                rf"IDS_PH_CRASH_(?:DUMP_)?{suffix}_BUTTON\s*,\s*L\"[^\"]+\"\s*\)\s*\}}",
            )
        self.assertEqual(crash.count("PhGetApplicationUiStringOrDefault("), 9)
        self.assertIn("IDS_PH_CRASH_TITLE", crash)
        self.assertIn("IDS_PH_CRASH_MINIDUMP_PROMPT", crash)
        self.assertNotIn("PH_AUTO(", crash)
        self.assertRegex(
            crash,
            r"if\s*\(PhpPreviousUnhandledExceptionFilter\)\s*"
            r"return PhpPreviousUnhandledExceptionFilter\(ExceptionInfo\);\s*"
            r"return EXCEPTION_CONTINUE_SEARCH;",
        )
        release_branch = crash.split("#else", 1)[1].split("#endif", 1)[0]
        self.assertIn('L"%s\\r\\n0x%08X (%s)"', release_branch)
        self.assertNotIn('L"%s\\r\\n0x%08X (%s)\\r\\n%s"', release_branch)

    def test_ksi_thread_stack_and_service_paths_are_native_and_lifetime_safe(self) -> None:
        ksi = self.audit.mask_c_comments(self.sources["ksisup.c"])
        thread = self.audit.mask_c_comments(self.sources["thrdstk.c"])
        service = self.audit.mask_c_comments(self.sources["srvprp.c"])

        for resource in (
            "IDS_PH_KSI_INITIALIZING_DRIVER", "IDS_PH_KSI_INITIAL_ELAPSED",
            "IDS_PH_KSI_SUPPORT_PENDING_TITLE", "IDS_PH_KSI_SUPPORT_PENDING_CONTENT",
            "IDS_PH_KSI_UNSUPPORTED_TITLE", "IDS_PH_KSI_UNSUPPORTED_CANARY_CONTENT",
            "IDS_PH_KSI_UNSUPPORTED_STABLE_CONTENT", "IDS_PH_KSI_CHECKING_PLATFORM_UPDATE",
        ):
            self.assertIn(f"PhGetApplicationUiString({resource})", ksi)

        event = function_body(thread, "PhpSymbolProviderEventCallbackHandler")
        timer = function_body(thread, "PhpThreadStackTaskDialogCallback")
        show = function_body(thread, "PhpShowThreadStackWindow")
        self.assertIn("PhCreateString(PhGetApplicationUiString(IDS_PH_THREAD_STACK_LOADING_SYMBOLS))", event)
        for body in (timer, show):
            self.assertIn("PhGetApplicationUiString(IDS_PH_THREAD_STACK_PROCESSING_FRAMES)", body)
            self.assertIn("PhGetApplicationUiString(IDS_PH_THREAD_STACK_LOADING_IMAGE_SYMBOLS)", body)
        self.assertGreaterEqual(thread.count("PhCreateString(PhGetApplicationUiString(IDS_PH_THREAD_STACK_PROCESSING_FRAMES))"), 2)
        self.assertRegex(
            thread,
            r"PhFormatString\(\s*PhGetApplicationUiString\(IDS_PH_THREAD_STACK_PROCESSING_FRAME_FORMAT\),\s*threadStackContext->NewList->Count",
        )
        self.assertIn("PhSetWindowText(context->PassBoxWindowHandle, PhGetApplicationUiString(IDS_PH_SERVICE_PASSWORD_PLACEHOLDER));", service)

    def test_target_raw_literals_leave_the_five_source_files(self) -> None:
        masked = "\n".join(self.audit.mask_c_comments(source) for source in self.sources.values())
        migrated_literals = tuple(
            literal for literal in TARGET_LITERALS if literal not in EARLY_CRASH_FALLBACKS
        )
        for literal in migrated_literals + LEGACY_DEBUGGER_LITERALS:
            escaped = literal.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
            with self.subTest(literal=literal):
                self.assertFalse(f'L"{escaped}"' in masked, msg=f"raw literal remains: {literal!r}")

    def test_fresh_target_scan_has_no_unmigrated_callsite_text(self) -> None:
        entries = []
        for name in SOURCE_FILES:
            self.audit.scan_c_file(str(APP_ROOT / name), entries)

        self.assertFalse(
            [
                entry
                for entry in entries
                if entry["category"]
                in {"c_taskdialog", "c_taskdialog_raw", "c_runtime_composed", "c_window_text"}
                and entry["english"] in TARGET_LITERALS
            ]
        )


if __name__ == "__main__":
    unittest.main()
