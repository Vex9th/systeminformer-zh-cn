#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

RESOURCES = r"""
IDS_PH_MENU_COMBINE_MEMORY_PAGES|3370|&Combine memory pages|合并内存页(&C)
IDS_PH_MENU_EMPTY_COMPRESSION_CACHE|3371|Empty &compression cache|清空压缩缓存(&C)
IDS_PH_MENU_EMPTY_SYSTEM_FILE_CACHE|3372|Empty system &file cache|清空系统文件缓存(&F)
IDS_PH_MENU_EMPTY_REGISTRY_CACHE|3373|Empty &registry cache|清空注册表缓存(&R)
IDS_PH_MENU_EMPTY_WORKING_SETS|3374|Empty &working sets|清空工作集(&W)
IDS_PH_MENU_EMPTY_MODIFIED_PAGE_LIST|3375|Empty &modified page list|清空已修改页列表(&M)
IDS_PH_MENU_EMPTY_MODIFIED_FILE_CACHE|3376|Empty &modified file cache|清空已修改文件缓存(&M)
IDS_PH_MENU_EMPTY_STANDBY_LIST|3377|Empty &standby list|清空备用列表(&S)
IDS_PH_MENU_EMPTY_PRIORITY_ZERO_STANDBY_LIST|3378|Empty &priority 0 standby list|清空优先级 0 备用列表(&P)
IDS_PH_MENU_EMPTY_ALL|3379|Empty &all|全部清空(&A)
IDS_PH_MENU_CONNECT|3380|&Connect|连接(&C)
IDS_PH_MENU_DISCONNECT|3381|&Disconnect|断开连接(&D)
IDS_PH_MENU_LOGOFF|3382|&Logoff|注销(&L)
IDS_PH_MENU_REMOTE_CONTROL|3383|Rem&ote control|远程控制(&O)
IDS_PH_MENU_SEND_MESSAGE|3384|Send &message...|发送消息(&M)...
IDS_PH_MENU_RESTART_TO_BOOT_APPLICATION|3385|Restart to boot application|重启进入引导应用程序
IDS_PH_MENU_RESTART_TO_FIRMWARE_APPLICATION|3386|Restart to firmware application|重启进入固件应用程序
IDS_PH_MENU_INSPECT_PLAIN|3387|&Inspect|检查(&I)
IDS_PH_MENU_OPEN_FILE_LOCATION_PLAIN|3388|Open &file location|打开文件位置(&F)
IDS_PH_MENU_UNLOAD_ALT|3389|Un&load|卸载(&L)
IDS_PH_MENU_STATISTICS_SHORTCUT|3390|S&tatistics|统计(&T)
IDS_PH_MENU_HIDE_DEFAULT_NAMESPACE|3391|Hide default namespace|隐藏默认命名空间
IDS_PH_MENU_HIGHLIGHT_DEFAULT_NAMESPACE|3392|Highlight default namespace|高亮默认命名空间
""".strip()

NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english, chinese)
    for symbol, resource_id, english, chinese in (
        line.split("|") for line in RESOURCES.splitlines()
    )
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("high_density_menu_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class SystemInformerRemainingHighDensityMenuResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.sources = {
            name: cls.audit.mask_c_comments((APP_ROOT / name).read_text(encoding="utf-8-sig"))
            for name in ("memlists.c", "thrdstk.c", "actions.c", "prpgwmi.c")
        }

    def test_resources_and_routes_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        combined = "\n".join(self.sources.values())

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            expected = 2 if symbol in {"IDS_PH_MENU_INSPECT_PLAIN", "IDS_PH_MENU_OPEN_FILE_LOCATION_PLAIN"} else 1
            self.assertEqual(expected, combined.count(f"PhGetApplicationUiString({symbol})"))

        expected_reused = {
            "IDS_PH_SEARCH_COPY": 1,
            "IDS_PH_MAINWND_MENU_PROPERTIES": 1,
            "IDS_PH_MAINWND_MENU_SUSPEND": 1,
            "IDS_PH_MAINWND_MENU_RESUME": 1,
            "IDS_PH_MENU_HIDE_USER_FRAMES": 1,
            "IDS_PH_MENU_HIDE_SYSTEM_FRAMES": 1,
            "IDS_PH_MENU_HIDE_INLINE_FRAMES": 1,
            "IDS_PH_MENU_HIGHLIGHT_USER_FRAMES": 1,
            "IDS_PH_MENU_HIGHLIGHT_SYSTEM_FRAMES": 1,
            "IDS_PH_MENU_HIGHLIGHT_INLINE_FRAMES": 1,
        }
        for symbol, count in expected_reused.items():
            self.assertEqual(count, combined.count(f"PhGetApplicationUiString({symbol})"))

    def test_target_files_have_no_direct_emenu_text(self) -> None:
        for name in self.sources:
            entries = []
            self.audit.scan_c_file(str(APP_ROOT / name), entries)
            self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
