#!/usr/bin/env python3

import importlib.util
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"


RESOURCES = r"""
IDS_PH_MENU_UNLOAD_SHORTCUT|3306|&Unload\bDel|卸载(&U)\bDel
IDS_PH_MENU_HIDE_DYNAMIC|3307|Hide dynamic|隐藏动态模块
IDS_PH_MENU_HIDE_KNOWNDLLS_IMAGES|3308|Hide knowndlls images|隐藏 KnownDLLs 映像
IDS_PH_MENU_HIDE_LOW_IMAGE_COHERENCY|3309|Hide low image coherency|隐藏映像低一致性模块
IDS_PH_MENU_HIDE_MAPPED|3310|Hide mapped|隐藏映射模块
IDS_PH_MENU_HIDE_STATIC|3311|Hide static|隐藏静态模块
IDS_PH_MENU_HIDE_VERIFIED|3312|Hide verified|隐藏已验证模块
IDS_PH_MENU_HIGHLIGHT_DOTNET_MODULES|3313|Highlight .NET modules|高亮 .NET 模块
IDS_PH_MENU_HIGHLIGHT_IMMERSIVE_MODULES|3314|Highlight immersive modules|高亮沉浸式模块
IDS_PH_MENU_HIGHLIGHT_KNOWNDLLS_IMAGES|3315|Highlight knowndlls images|高亮 KnownDLLs 映像
IDS_PH_MENU_HIGHLIGHT_LOW_IMAGE_COHERENCY|3316|Highlight low image coherency|高亮映像低一致性模块
IDS_PH_MENU_HIGHLIGHT_MAPPED_MODULES|3317|Highlight mapped modules|高亮映射模块
IDS_PH_MENU_HIGHLIGHT_NATIVE_MODULES|3318|Highlight native modules|高亮原生模块
IDS_PH_MENU_HIGHLIGHT_RELOCATED_MODULES|3319|Highlight relocated modules|高亮已重定位模块
IDS_PH_MENU_HIGHLIGHT_SYSTEM_MODULES|3320|Highlight system modules|高亮系统模块
IDS_PH_MENU_HIGHLIGHT_UNTRUSTED_MODULES|3321|Highlight untrusted modules|高亮不受信任模块
IDS_PH_MENU_LOAD_MODULE|3322|Load module...|加载模块...
IDS_PH_MENU_ZERO_PAD_ADDRESSES|3323|Zero pad addresses|地址补零
""".strip()


NEW_RESOURCES = tuple(
    (symbol, int(resource_id), english.replace("\\b", "\b"), chinese.replace("\\b", "\b"))
    for symbol, resource_id, english, chinese in (
        line.split("|") for line in RESOURCES.splitlines()
    )
)


def load_audit_module():
    path = REPO_ROOT / "tools" / "zhcn" / "audit.py"
    spec = importlib.util.spec_from_file_location("module_menu_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"').replace("\\b", "\b")
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class SystemInformerModuleMenuNativeResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_audit_module()
        cls.source = cls.audit.mask_c_comments(
            (APP_ROOT / "prpgmod.c").read_text(encoding="utf-8-sig")
        )

    def test_resources_and_routes_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))
            self.assertEqual(
                1,
                len(re.findall(rf"PhGetApplicationUiString\(\s*{symbol}\s*\)", self.source)),
            )

        self.assertEqual(
            1,
            len(re.findall(r"PhGetApplicationUiString\(\s*IDS_PH_MAINWND_MENU_PROPERTIES\s*\)", self.source)),
        )
        self.assertEqual(
            1,
            len(re.findall(r"PhGetApplicationUiString\(\s*IDS_PH_MENU_SAVE\s*\)", self.source)),
        )

    def test_resource_tail_and_fresh_scan_are_exact(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_MENU_COLLAPSE_ALL_PLAIN$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3370$")

        entries = []
        self.audit.scan_c_file(str(APP_ROOT / "prpgmod.c"), entries)
        self.assertEqual([], [entry for entry in entries if entry["category"] == "c_emenu"])


if __name__ == "__main__":
    unittest.main()
