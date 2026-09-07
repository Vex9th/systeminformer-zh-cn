import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SOURCE_PATH = REPO_ROOT / "SystemInformer" / "envdlg.c"


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"function not found: {name}")

    opening_brace = source.find("{", match.start())
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index]

    raise AssertionError(f"unterminated function: {name}")


class EnvironmentVariablesAsyncWindowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE_PATH.read_text(encoding="utf-8-sig")
        cls.compact_source = compact(cls.source)

    def test_shared_window_state_has_one_initialized_lock(self) -> None:
        self.assertIn(
            "staticPH_QUEUED_LOCKEtEnvironmentVariablesWindowLock=PH_QUEUED_LOCK_INIT;",
            self.compact_source,
        )

    def test_worker_uses_local_window_and_publishes_and_clears_under_lock(self) -> None:
        worker = compact(function_body(self.source, "EtEnvironmentVariablesWindowThreadStart"))

        self.assertIn("HWNDwindowHandle;", worker)
        self.assertIn("windowHandle=PhCreateDialog(", worker)
        self.assertNotIn(
            "EtEnvironmentVariablesWindowHandle=PhCreateDialog(",
            worker,
        )
        self.assertIn(
            "PhAcquireQueuedLockExclusive(&EtEnvironmentVariablesWindowLock);"
            "EtEnvironmentVariablesWindowHandle=windowHandle;"
            "PhReleaseQueuedLockExclusive(&EtEnvironmentVariablesWindowLock);",
            worker,
        )
        self.assertNotIn(
            "IsDialogMessage(EtEnvironmentVariablesWindowHandle,&message)",
            worker,
        )
        self.assertIn("IsDialogMessage(windowHandle,&message)", worker)

        cleanup_acquire = worker.rindex(
            "PhAcquireQueuedLockExclusive(&EtEnvironmentVariablesWindowLock);"
        )
        window_clear = worker.index(
            "if(EtEnvironmentVariablesWindowHandle==windowHandle)"
            "EtEnvironmentVariablesWindowHandle=NULL;",
            cleanup_acquire,
        )
        close_handle = worker.index(
            "NtClose(EtEnvironmentVariablesWindowThreadHandle);",
            window_clear,
        )
        thread_clear = worker.index(
            "EtEnvironmentVariablesWindowThreadHandle=NULL;",
            close_handle,
        )
        cleanup_release = worker.index(
            "PhReleaseQueuedLockExclusive(&EtEnvironmentVariablesWindowLock);",
            thread_clear,
        )
        self.assertLess(cleanup_acquire, window_clear)
        self.assertLess(window_clear, close_handle)
        self.assertLess(close_handle, thread_clear)
        self.assertLess(thread_clear, cleanup_release)

    def test_creator_serializes_thread_creation_and_snapshots_window(self) -> None:
        show_start = self.source.index("VOID PhShowEnvironmentVariablesDialog")
        show_body = compact(self.source[show_start:])
        acquire = show_body.index(
            "PhAcquireQueuedLockExclusive(&EtEnvironmentVariablesWindowLock);"
        )
        create = show_body.index("PhCreateThreadEx(")
        release = show_body.index(
            "PhReleaseQueuedLockExclusive(&EtEnvironmentVariablesWindowLock);"
        )
        self.assertLess(acquire, create)
        self.assertLess(create, release)
        self.assertIn(
            "windowHandle=EtEnvironmentVariablesWindowHandle;",
            show_body,
        )
        self.assertIn("if(windowHandle)PostMessage(windowHandle,", show_body)


if __name__ == "__main__":
    unittest.main()
