import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
THREAD_LIST_SOURCE = ROOT / "SystemInformer" / "thrdlist.c"


def _extract_braced_block(source: str, open_brace: int) -> tuple[str, int]:
    depth = 0

    for index in range(open_brace, len(source)):
        character = source[index]

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                return source[open_brace + 1 : index], index + 1

    raise AssertionError("unterminated C block")


def _extract_if_else(source: str, condition: str) -> tuple[str, str]:
    condition_start = source.index(condition)
    true_open = source.index("{", condition_start + len(condition))
    true_block, after_true = _extract_braced_block(source, true_open)
    else_start = source.index("else", after_true)
    false_open = source.index("{", else_start + len("else"))
    false_block, _ = _extract_braced_block(source, false_open)
    return true_block, false_block


class ThreadLastSystemCallLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = THREAD_LIST_SOURCE.read_text(encoding="utf-8")
        cls.named_call_branch, cls.unnamed_call_branch = _extract_if_else(
            cls.source,
            "if (systemCallName = PhGetSystemCallNumberName(",
        )

    def _assert_wait_time_released_after_format(self, branch: str) -> None:
        _, windows_8_or_later = _extract_if_else(
            branch,
            "if (WindowsVersion < WINDOWS_8)",
        )

        declaration = "PPH_STRING waitTime;"
        assignment = "waitTime = PhFormatTimeSpanRelative("
        reference = re.search(
            r"PhInitFormatSR\(\s*&format\[\d+\],\s*waitTime->sr\s*\);",
            windows_8_or_later,
        )
        formatting = "PhMoveReference(&node->LastSystemCallText, PhFormat("
        release = "PhDereferenceObject(waitTime);"

        self.assertIsNotNone(reference)
        self.assertEqual(windows_8_or_later.count(declaration), 1)
        self.assertEqual(windows_8_or_later.count(assignment), 1)
        self.assertEqual(windows_8_or_later.count(release), 1)
        self.assertLess(windows_8_or_later.index(assignment), reference.start())
        self.assertLess(reference.end(), windows_8_or_later.index(formatting))
        self.assertLess(windows_8_or_later.index(formatting), windows_8_or_later.index(release))

    def test_named_system_call_branch_releases_wait_time_after_formatting(self) -> None:
        self._assert_wait_time_released_after_format(self.named_call_branch)

    def test_unnamed_system_call_branch_releases_wait_time_after_formatting(self) -> None:
        self._assert_wait_time_released_after_format(self.unnamed_call_branch)


if __name__ == "__main__":
    unittest.main()
