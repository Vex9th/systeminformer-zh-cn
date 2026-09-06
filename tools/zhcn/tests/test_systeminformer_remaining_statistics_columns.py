#!/usr/bin/env python3

import json
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "SystemInformer"

NEW_RESOURCES = (
    ("IDS_PH_STAT_IOOTHER", 2944, "I/O other", "I/O 其他"),
    ("IDS_PH_STAT_IOOTHERBYTES", 2945, "I/O other bytes", "I/O 其他字节"),
    ("IDS_PH_STAT_IOREADBYTES", 2946, "I/O read bytes", "I/O 读取字节"),
    ("IDS_PH_STAT_IOREADS", 2947, "I/O reads", "I/O 读取"),
    ("IDS_PH_STAT_IOWRITEBYTES", 2948, "I/O write bytes", "I/O 写入字节"),
    ("IDS_PH_STAT_IOWRITES", 2949, "I/O writes", "I/O 写入"),
)

ROUTES = {
    "proctree.c": {
        "IDS_PH_STAT_CPU": 1,
        "IDS_PH_STAT_CPUAVERAGE": 1,
        "IDS_PH_STAT_GDIHANDLES": 1,
        "IDS_PH_STAT_IOPRIORITY": 1,
        "IDS_PH_STAT_KERNELTIME": 0,
        "IDS_PH_STAT_PAGEFAULTS": 1,
        "IDS_PH_STAT_PAGEFAULTSDELTA": 1,
        "IDS_PH_STAT_PEAKPRIVATEBYTES": 1,
        "IDS_PH_STAT_PEAKVIRTUALSIZE": 1,
        "IDS_PH_STAT_PEAKWORKINGSET": 1,
        "IDS_PH_STAT_PRIORITY": 0,
        "IDS_PH_STAT_PRIVATEBYTES": 1,
        "IDS_PH_STAT_PRIVATEBYTESDELTA": 1,
        "IDS_PH_STAT_SHAREDCOMMIT": 1,
        "IDS_PH_STAT_USERHANDLES": 1,
        "IDS_PH_STAT_USERTIME": 0,
        "IDS_PH_STAT_VIRTUALSIZE": 1,
        "IDS_PH_STAT_WORKINGSET": 1,
        "IDS_PH_STAT_IOOTHER": 1,
        "IDS_PH_STAT_IOOTHERBYTES": 1,
        "IDS_PH_STAT_IOREADBYTES": 1,
        "IDS_PH_STAT_IOREADS": 1,
        "IDS_PH_STAT_IOWRITEBYTES": 1,
        "IDS_PH_STAT_IOWRITES": 1,
    },
    "thrdlist.c": {
        "IDS_PH_STAT_CPU": 1,
        "IDS_PH_STAT_IOPRIORITY": 1,
        "IDS_PH_STAT_KERNELTIME": 1,
        "IDS_PH_STAT_PRIORITY": 1,
        "IDS_PH_STAT_USERTIME": 1,
        "IDS_PH_STAT_IOOTHER": 1,
        "IDS_PH_STAT_IOOTHERBYTES": 1,
        "IDS_PH_STAT_IOREADBYTES": 1,
        "IDS_PH_STAT_IOREADS": 1,
        "IDS_PH_STAT_IOWRITEBYTES": 1,
        "IDS_PH_STAT_IOWRITES": 1,
    },
    "memlist.c": {"IDS_PH_STAT_PRIORITY": 1},
}

COLUMN_BINDINGS = {
    "proctree.c": (
        ("PHPRTLC_CPU", "IDS_PH_STAT_CPU"),
        ("PHPRTLC_PRIVATEBYTES", "IDS_PH_STAT_PRIVATEBYTES"),
        ("PHPRTLC_PEAKPRIVATEBYTES", "IDS_PH_STAT_PEAKPRIVATEBYTES"),
        ("PHPRTLC_WORKINGSET", "IDS_PH_STAT_WORKINGSET"),
        ("PHPRTLC_PEAKWORKINGSET", "IDS_PH_STAT_PEAKWORKINGSET"),
        ("PHPRTLC_VIRTUALSIZE", "IDS_PH_STAT_VIRTUALSIZE"),
        ("PHPRTLC_PEAKVIRTUALSIZE", "IDS_PH_STAT_PEAKVIRTUALSIZE"),
        ("PHPRTLC_PAGEFAULTS", "IDS_PH_STAT_PAGEFAULTS"),
        ("PHPRTLC_GDIHANDLES", "IDS_PH_STAT_GDIHANDLES"),
        ("PHPRTLC_USERHANDLES", "IDS_PH_STAT_USERHANDLES"),
        ("PHPRTLC_IOPRIORITY", "IDS_PH_STAT_IOPRIORITY"),
        ("PHPRTLC_PAGEFAULTSDELTA", "IDS_PH_STAT_PAGEFAULTSDELTA"),
        ("PHPRTLC_IOREADS", "IDS_PH_STAT_IOREADS"),
        ("PHPRTLC_IOWRITES", "IDS_PH_STAT_IOWRITES"),
        ("PHPRTLC_IOOTHER", "IDS_PH_STAT_IOOTHER"),
        ("PHPRTLC_IOREADBYTES", "IDS_PH_STAT_IOREADBYTES"),
        ("PHPRTLC_IOWRITEBYTES", "IDS_PH_STAT_IOWRITEBYTES"),
        ("PHPRTLC_IOOTHERBYTES", "IDS_PH_STAT_IOOTHERBYTES"),
        ("PHPRTLC_PRIVATEBYTESDELTA", "IDS_PH_STAT_PRIVATEBYTESDELTA"),
        ("PHPRTLC_COMMITSIZE", "IDS_PH_STAT_SHAREDCOMMIT"),
        ("PHPRTLC_CPUAVERAGE", "IDS_PH_STAT_CPUAVERAGE"),
    ),
    "thrdlist.c": (
        ("PH_THREAD_TREELIST_COLUMN_CPU", "IDS_PH_STAT_CPU"),
        ("PH_THREAD_TREELIST_COLUMN_PRIORITY", "IDS_PH_STAT_PRIORITY"),
        ("PH_THREAD_TREELIST_COLUMN_IOPRIORITY", "IDS_PH_STAT_IOPRIORITY"),
        ("PH_THREAD_TREELIST_COLUMN_KERNELTIME", "IDS_PH_STAT_KERNELTIME"),
        ("PH_THREAD_TREELIST_COLUMN_USERTIME", "IDS_PH_STAT_USERTIME"),
        ("PH_THREAD_TREELIST_COLUMN_IOREADS", "IDS_PH_STAT_IOREADS"),
        ("PH_THREAD_TREELIST_COLUMN_IOWRITES", "IDS_PH_STAT_IOWRITES"),
        ("PH_THREAD_TREELIST_COLUMN_IOOTHER", "IDS_PH_STAT_IOOTHER"),
        ("PH_THREAD_TREELIST_COLUMN_IOREADBYTES", "IDS_PH_STAT_IOREADBYTES"),
        ("PH_THREAD_TREELIST_COLUMN_IOWRITEBYTES", "IDS_PH_STAT_IOWRITEBYTES"),
        ("PH_THREAD_TREELIST_COLUMN_IOOTHERBYTES", "IDS_PH_STAT_IOOTHERBYTES"),
    ),
    "memlist.c": (("PHMMTLC_PRIORITY", "IDS_PH_STAT_PRIORITY"),),
}

MIGRATED_KEYS = {
    "CPU",
    "CPU (average)",
    "GDI handles",
    "I/O priority",
    "Kernel time",
    "Page faults",
    "Page faults delta",
    "Peak private bytes",
    "Peak virtual size",
    "Peak working set",
    "Priority",
    "Private bytes",
    "Private bytes delta",
    "Shared commit",
    "USER handles",
    "User time",
    "Virtual size",
    "Working set",
    *(english for _symbol, _resource_id, english, _chinese in NEW_RESOURCES),
}

RUNTIME_COMPATIBILITY_KEYS = {"CPU", "Private bytes", "Working set"}


def parse_stringtable(path: pathlib.Path) -> dict[str, str]:
    return {
        symbol: value.replace('""', '"')
        for symbol, value in re.findall(
            r'(?m)^\s*(IDS_PH_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            path.read_text(encoding="utf-8-sig"),
        )
    }


class SystemInformerRemainingStatisticsColumnsTests(unittest.TestCase):
    def test_new_resources_are_contiguous_bilingual_and_native_owned(self) -> None:
        header = (APP_ROOT / "resource.h").read_text(encoding="utf-8-sig")
        english = parse_stringtable(APP_ROOT / "SystemInformer.rc")
        chinese = parse_stringtable(APP_ROOT / "SystemInformer.zh-cn.rc")
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))

        for symbol, resource_id, en, zh in NEW_RESOURCES:
            self.assertRegex(header, rf"(?m)^#define\s+{symbol}\s+{resource_id}$")
            self.assertEqual(en, english.get(symbol))
            self.assertEqual(zh, chinese.get(symbol))

        self.assertEqual(1296, len(english))
        self.assertEqual(1296, len(chinese))
        self.assertRegex(header, r"(?m)^#define IDS_PH_LAST\s+IDS_PH_TREENEW_WINDOW_TITLE$")
        self.assertRegex(header, r"(?m)^#define _APS_NEXT_SYMED_VALUE\s+3296$")

        for en in MIGRATED_KEYS:
            owner = "strings" if en in RUNTIME_COMPATIBILITY_KEYS else "native_strings"
            other = "native_strings" if owner == "strings" else "strings"
            self.assertIn(en, data[owner])
            self.assertNotIn(en, data[other])

    def test_all_33_column_routes_use_application_lifetime_resources(self) -> None:
        total = 0
        for file_name, bindings in COLUMN_BINDINGS.items():
            source = (APP_ROOT / file_name).read_text(encoding="utf-8-sig")
            for column, symbol in bindings:
                pattern = rf"PhAddTreeNewColumn(?:Ex|Ex2)?\(\s*[^,]+,\s*{column}\s*,[^;]*?PhGetApplicationUiString\(\s*{symbol}\s*\)"
                self.assertEqual(1, len(re.findall(pattern, source, re.S)), (file_name, column, symbol))
                total += 1
        self.assertEqual(33, total)

    def test_target_column_literals_are_removed_from_product_sources(self) -> None:
        residuals = []
        for path in APP_ROOT.rglob("*"):
            if path.suffix.lower() not in {".c", ".cc", ".cpp", ".cxx"}:
                continue
            source = path.read_text(encoding="utf-8-sig")
            for english in MIGRATED_KEYS:
                residuals.extend(
                    (path.relative_to(REPO_ROOT).as_posix(), english)
                    for _match in re.finditer(rf'\bL"{re.escape(english)}"', source)
                )
        self.assertEqual(
            sorted([
                *(('SystemInformer/options.c', 'Private bytes') for _ in range(2)),
                ('SystemInformer/miniinfo.c', 'Private bytes'),
                ('SystemInformer/miniinfo.c', 'Working set'),
                *(('SystemInformer/miniinfo.c', 'CPU') for _ in range(4)),
                ('SystemInformer/sysinfo.c', 'CPU'),
                ('SystemInformer/notifico.c', 'CPU'),
            ]),
            sorted(residuals),
        )


if __name__ == "__main__":
    unittest.main()
