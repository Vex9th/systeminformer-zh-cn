import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

ES_ROOT = REPO_ROOT / "plugins" / "ExtendedServices"
UN_ROOT = REPO_ROOT / "plugins" / "UserNotes"

ES_RESOURCES = {
    "IDS_ES_TRIGGER_DATA_NOT_ALLOWED_FORMAT": (
        2066,
        'The trigger type "%s" does not allow data items to be configured.',
        "触发器类型“%s”不允许配置数据项。",
    ),
    "IDS_ES_DEFAULT_RESTART_MESSAGE_FORMAT": (
        2067,
        "Your computer is connected to the computer named %s. The %s service on %s has ended unexpectedly. %s will restart automatically, and then you can reestablish the connection.",
        "你的计算机已连接到名为 %s 的计算机。%s 服务在 %s 上意外终止。%s 将自动重启，随后你可以重新建立连接。",
    ),
    "IDS_ES_NOT_AVAILABLE": (2068, "N/A", "不适用"),
    "IDS_ES_COMPUTER_NAME_UNKNOWN": (2069, "(unknown)", "（未知）"),
}

UN_RESOURCES = {
    "IDS_UN_DB_TYPE_FILE": (2015, "File", "文件"),
    "IDS_UN_DB_TYPE_SERVICE": (2016, "Service", "服务"),
    "IDS_UN_DB_TYPE_COMMAND_LINE": (2017, "Commandline", "命令行"),
    "IDS_UN_STATUS_TRUE": (2018, "True", "真"),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def function_body(source: str, function_name: str) -> str:
    for match in re.finditer(rf"\b{re.escape(function_name)}\s*\(", source):
        brace = source.find("{", match.end())
        semicolon = source.find(";", match.end())

        if brace < 0 or (semicolon >= 0 and semicolon < brace):
            continue

        depth = 0
        index = brace
        state = "code"

        while index < len(source):
            char = source[index]
            next_char = source[index + 1] if index + 1 < len(source) else ""

            if state == "code":
                if char == '"':
                    state = "string"
                elif char == "'":
                    state = "character"
                elif char == "/" and next_char == "/":
                    state = "line_comment"
                    index += 1
                elif char == "/" and next_char == "*":
                    state = "block_comment"
                    index += 1
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return source[brace:index + 1]
            elif state in {"string", "character"}:
                if char == "\\":
                    index += 1
                elif (state == "string" and char == '"') or (
                    state == "character" and char == "'"
                ):
                    state = "code"
            elif state == "line_comment":
                if char == "\n":
                    state = "code"
            elif state == "block_comment" and char == "*" and next_char == "/":
                state = "code"
                index += 1

            index += 1

    raise AssertionError(f"function definition not found: {function_name}")


def rc_strings(path: Path) -> dict[str, str]:
    return {
        resource_id: value.replace('""', '"')
        for resource_id, value in re.findall(
            r'^\s*(IDS_[A-Z0-9_]+)\s+"((?:[^"]|"")*)"\s*$',
            read(path),
            re.MULTILINE,
        )
    }


class SmallPluginRemainingResourceTests(unittest.TestCase):
    def test_extended_services_resources_are_contiguous_and_bilingual(self) -> None:
        header = read(ES_ROOT / "resource.h")
        english = rc_strings(ES_ROOT / "ExtendedServices.rc")
        chinese = rc_strings(ES_ROOT / "ExtendedServices.zh-cn.rc")

        for resource_id, (number, english_text, chinese_text) in ES_RESOURCES.items():
            with self.subTest(resource_id=resource_id):
                self.assertRegex(
                    header,
                    rf"(?m)^#define\s+{resource_id}\s+{number}$",
                )
                self.assertEqual(english.get(resource_id), english_text)
                self.assertEqual(chinese.get(resource_id), chinese_text)

        self.assertRegex(
            header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2090$",
        )

    def test_user_notes_resources_are_contiguous_and_bilingual(self) -> None:
        header = read(UN_ROOT / "resource.h")
        english = rc_strings(UN_ROOT / "UserNotes.rc")
        chinese = rc_strings(UN_ROOT / "UserNotes.zh-cn.rc")

        for resource_id, (number, english_text, chinese_text) in UN_RESOURCES.items():
            with self.subTest(resource_id=resource_id):
                self.assertRegex(
                    header,
                    rf"(?m)^#define\s+{resource_id}\s+{number}$",
                )
                self.assertEqual(english.get(resource_id), english_text)
                self.assertEqual(chinese.get(resource_id), chinese_text)

        self.assertRegex(
            header,
            r"(?m)^#define\s+_APS_NEXT_SYMED_VALUE\s+2052$",
        )

    def test_trigger_warning_uses_localized_format_inside_explicit_auto_pool(self) -> None:
        source = read(ES_ROOT / "trigger.c")
        body = function_body(source, "EspServiceTriggerDlgProc")
        literal = 'L"The trigger type \\"%s\\" does not allow data items to be configured."'

        self.assertNotRegex(body, rf"PhaFormatString\(\s*{re.escape(literal)}")
        self.assertEqual(body.count("IDS_ES_TRIGGER_DATA_NOT_ALLOWED_FORMAT"), 1)
        self.assertRegex(
            body,
            r"warningFormat\s*=\s*PhLoadUiString\(\s*PluginInstance->DllBase,\s*"
            r"IDS_ES_TRIGGER_DATA_NOT_ALLOWED_FORMAT,\s*NULL\s*\);",
        )
        self.assertIn(
            'warningFormatText = PhGetStringOrDefault(warningFormat, L"The trigger type \\"%s\\" does not allow data items to be configured.")',
            body,
        )
        self.assertRegex(
            body,
            r"PhaFormatString\(\s*warningFormatText,\s*PhGetString\(typeString\)\s*\)",
        )
        self.assertEqual(body.count("PhClearReference(&warningFormat)"), 1)
        self.assertLess(body.index("PhInitializeAutoPool"), body.index("IDS_ES_TRIGGER_DATA_NOT_ALLOWED_FORMAT"))
        self.assertLess(body.index("PhShowMessage2"), body.index("PhClearReference(&warningFormat)"))
        self.assertLess(body.index("PhClearReference(&warningFormat)"), body.index("PhDeleteAutoPool"))

    def test_restart_message_preserves_argument_order_and_explicit_lifetimes(self) -> None:
        source = read(ES_ROOT / "recovery.c")
        body = function_body(source, "RestartComputerDlgProc")

        self.assertNotRegex(
            body,
            r'PhFormatString\(\s*L"Your computer is connected to the computer named %s\.',
        )
        self.assertNotIn('computerName = L"(unknown)"', body)
        self.assertEqual(body.count("IDS_ES_DEFAULT_RESTART_MESSAGE_FORMAT"), 1)
        self.assertEqual(body.count("IDS_ES_COMPUTER_NAME_UNKNOWN"), 1)
        self.assertNotIn("messageFormat->Buffer", body)
        self.assertNotIn("computerNameFallback->Buffer", body)
        self.assertIn(
            'computerNameFallbackText = PhGetStringOrDefault(computerNameFallback, L"(unknown)")',
            body,
        )
        self.assertRegex(
            body,
            r'messageFormatText\s*=\s*PhGetStringOrDefault\(\s*messageFormat,\s*'
            r'L"Your computer is connected to the computer named %s\. "',
        )
        self.assertRegex(
            body,
            r"message\s*=\s*PhFormatString\(\s*messageFormatText,\s*"
            r"computerName,\s*context->ServiceItem->Name->Buffer,\s*"
            r"computerName,\s*computerName\s*\);",
        )

        set_index = body.index("PhSetDialogItemText(WindowHandle, IDC_RESTARTMESSAGE, PhGetString(message))")
        message_release_index = body.index("PhClearReference(&message)")
        format_release_index = body.index("PhClearReference(&messageFormat)")
        fallback_release_index = body.index("PhClearReference(&computerNameFallback)")
        self.assertEqual(body.count("PhClearReference(&message)"), 1)
        self.assertEqual(body.count("PhClearReference(&messageFormat)"), 1)
        self.assertEqual(body.count("PhClearReference(&computerNameFallback)"), 1)
        self.assertLess(body.index("message = PhFormatString"), set_index)
        self.assertLess(set_index, message_release_index)
        self.assertLess(message_release_index, format_release_index)
        self.assertLess(set_index, fallback_release_index)

    def test_extended_services_not_available_resource_covers_all_seven_sinks(self) -> None:
        other = read(ES_ROOT / "other.c")
        package = read(ES_ROOT / "svcpkg.c")
        other_body = function_body(other, "EspServiceOtherDlgProc")
        package_body = function_body(package, "EspUpdatePackageProperties")

        self.assertNotRegex(other_body, r'PhSetDialogItemText\([^;]*L"N/A"')
        self.assertNotRegex(package_body, r'PhSetDialogItemText\([^;]*L"N/A"')
        self.assertEqual(other_body.count("IDS_ES_NOT_AVAILABLE"), 1)
        self.assertNotIn("notAvailableString->Buffer", other_body)
        self.assertNotIn("notAvailableString->Buffer", package_body)
        self.assertIn(
            'notAvailableText = PhGetStringOrDefault(notAvailableString, L"N/A")',
            other_body,
        )
        self.assertIn(
            'notAvailableText = PhGetStringOrDefault(notAvailableString, L"N/A")',
            package_body,
        )
        self.assertEqual(package_body.count("PhGetStringOrDefault(string, notAvailableText)"), 6)
        self.assertEqual(package_body.count("IDS_ES_NOT_AVAILABLE"), 1)
        self.assertEqual(other_body.count("PhClearReference(&serviceSidString)"), 1)
        self.assertEqual(other_body.count("PhClearReference(&notAvailableString)"), 1)
        self.assertEqual(package_body.count("PhClearReference(&notAvailableString)"), 1)
        other_set_index = other_body.index("PhSetDialogItemText(")
        self.assertLess(other_set_index, other_body.index("PhClearReference(&serviceSidString)"))
        self.assertLess(other_set_index, other_body.index("PhClearReference(&notAvailableString)"))
        self.assertLess(
            package_body.rindex("PhGetStringOrDefault(string, notAvailableText)"),
            package_body.index("PhClearReference(&notAvailableString)"),
        )

    def test_user_notes_only_localizes_display_values(self) -> None:
        source = read(UN_ROOT / "options.c")
        body = function_body(source, "OptionsEnumDbCallback")

        for literal in ('L"File"', 'L"Service"', 'L"Commandline"', 'L"True"'):
            self.assertNotRegex(body, rf"PhSetListViewSubItem\([^;]*{re.escape(literal)}")

        expected_tag_bindings = {
            "FILE_TAG": ("IDS_UN_DB_TYPE_FILE", "File"),
            "SERVICE_TAG": ("IDS_UN_DB_TYPE_SERVICE", "Service"),
            "COMMAND_LINE_TAG": ("IDS_UN_DB_TYPE_COMMAND_LINE", "Commandline"),
        }
        for tag, (resource_id, default_text) in expected_tag_bindings.items():
            with self.subTest(tag=tag):
                self.assertRegex(
                    body,
                    rf"(?:if|else\s+if)\s*\(Object->Tag\s*==\s*{tag}\)\s*\{{\s*"
                    rf"OptionsSetListViewResourceSubItem\(\s*Context->ListViewHandle,\s*"
                    rf"lvItemIndex,\s*1,\s*{resource_id},\s*L\"{default_text}\"\s*\);\s*\}}",
                )

        self.assertEqual(body.count("IDS_UN_STATUS_TRUE"), 2)
        self.assertRegex(
            body,
            r"if\s*\(Object->Collapse\)\s*\{\s*OptionsSetListViewResourceSubItem\(\s*"
            r"Context->ListViewHandle,\s*lvItemIndex,\s*7,\s*IDS_UN_STATUS_TRUE,\s*L\"True\"\s*\);\s*\}",
        )
        self.assertRegex(
            body,
            r"if\s*\(Object->Efficiency\)\s*\{\s*OptionsSetListViewResourceSubItem\(\s*"
            r"Context->ListViewHandle,\s*lvItemIndex,\s*10,\s*IDS_UN_STATUS_TRUE,\s*L\"True\"\s*\);\s*\}",
        )
        self.assertIn("Object->Tag == FILE_TAG", body)
        self.assertIn("Object->Tag == SERVICE_TAG", body)
        self.assertIn("Object->Tag == COMMAND_LINE_TAG", body)

    def test_user_notes_resource_helper_releases_text_after_listview_copy(self) -> None:
        source = read(UN_ROOT / "options.c")
        helper = function_body(source, "OptionsSetListViewResourceSubItem")

        load_index = helper.index("PhLoadUiString")
        set_index = helper.index("PhSetListViewSubItem")
        self.assertIn("PhGetStringOrDefault(text, DefaultText)", helper)
        self.assertNotIn("text->Buffer", helper)
        release_index = helper.index("PhClearReference(&text)")
        self.assertEqual(helper.count("PhClearReference(&text)"), 1)
        self.assertLess(load_index, set_index)
        self.assertLess(set_index, release_index)

    def test_translation_entries_preserve_format_placeholders(self) -> None:
        data = json.loads((REPO_ROOT / "tools" / "zhcn" / "zh-CN.json").read_text(encoding="utf-8"))
        translations = {**data["strings"], **data["native_strings"]}

        for _, (_, english, chinese) in {**ES_RESOURCES, **UN_RESOURCES}.items():
            with self.subTest(english=english):
                self.assertEqual(translations.get(english), chinese)
                self.assertEqual(english.count("%s"), chinese.count("%s"))


if __name__ == "__main__":
    unittest.main()
