"""离线执行真实 C 查询函数，只替换 Windows 文件系统边界。"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class FileQueryBackportTests(unittest.TestCase):
    def test_empty_nonempty_error_and_buffer_growth(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("需要 C 编译器；Windows 原生用例另行覆盖空目录")
        source = (ROOT / "phlib/nativefile.c").read_text(encoding="utf-8-sig")
        start = source.index("NTSTATUS PhpQueryFileVariableSize(")
        end = source.index("\n/**", start)
        harness = r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#define _In_
#define _Out_
#define TRUE 1
#define NT_SUCCESS(s) ((s) >= 0)
#define STATUS_BUFFER_OVERFLOW (-1)
#define STATUS_BUFFER_TOO_SMALL (-2)
#define STATUS_INFO_LENGTH_MISMATCH (-3)
#define STATUS_NO_MORE_ENTRIES (-4)
typedef int32_t NTSTATUS;
typedef void *HANDLE, *PVOID;
typedef uint32_t ULONG;
typedef int FILE_INFORMATION_CLASS;
typedef struct { uintptr_t Information; } IO_STATUS_BLOCK;
static int scenario, calls, allocations;
static void *PhAllocate(ULONG size) { allocations++; return malloc(size); }
static void PhFree(void *p) { allocations--; free(p); }
static NTSTATUS NtQueryInformationFile(HANDLE h, IO_STATUS_BLOCK *io,
    void *buffer, ULONG size, FILE_INFORMATION_CLASS cls)
{
    (void)h; (void)cls;
    calls++;
    io->Information = 0;
    if (scenario == 2) return -5;
    if (scenario == 3 && calls == 1) return STATUS_BUFFER_TOO_SMALL;
    if (scenario == 1 || scenario == 3) {
        if (size < 4) return -6;
        *(uint32_t *)buffer = 42;
        io->Information = 4;
    }
    return 0;
}
'''
        main = r'''
int main(void) {
    int failures = 0;
    for (scenario = 0; scenario < 4; scenario++) {
        void *buffer = NULL;
        NTSTATUS status;
        calls = 0;
        status = PhpQueryFileVariableSize(NULL, 0, &buffer);
        if (scenario == 0 && (status != STATUS_NO_MORE_ENTRIES || buffer != NULL)) {
            puts("empty query returned success or an uninitialized buffer"); failures++;
        }
        if (scenario == 2 && (status != -5 || buffer != NULL)) failures++;
        if ((scenario == 1 || scenario == 3) &&
            (status != 0 || !buffer || *(uint32_t *)buffer != 42)) failures++;
        if (scenario == 3 && calls != 2) failures++;
        if (buffer) PhFree(buffer);
        if (allocations != 0) { puts("leaked query buffer"); failures++; }
    }
    return failures ? 1 : 0;
}
'''
        with tempfile.TemporaryDirectory() as temp:
            c_file = Path(temp) / "query.c"
            binary = Path(temp) / "query"
            c_file.write_text(harness + source[start:end] + main, encoding="utf-8")
            build = subprocess.run([compiler, "-std=c11", "-Wall", "-Werror", str(c_file), "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
