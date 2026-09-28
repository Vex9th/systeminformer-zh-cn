/* 上游修复的原生行为回归：使用畸形 PE 和真实设置表。 */
#include "tests.h"
#include <mapimg.h>
#include <settings.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

// 内部导出名查找函数；直接链接 phlib，验证映射末尾的边界行为。
ULONG PhLookupMappedImageExportName(PPH_MAPPED_IMAGE_EXPORTS Exports, PCSTR Name);

static ULONG Failures;

#define CHECK(condition) do { if (!(condition)) { \
    printf("FAIL: %s (line %d)\n", #condition, __LINE__); Failures++; \
} } while (0)

static VOID TestOptionalHeader(BOOLEAN Is64)
{
    PBYTE bytes = PhAllocateZero(1024);
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)bytes;
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)(bytes + 128);
    PH_MAPPED_IMAGE image;
    PIMAGE_DATA_DIRECTORY directory;
    PIMAGE_DATA_DIRECTORY directories;
    USHORT offset = Is64 ? FIELD_OFFSET(IMAGE_OPTIONAL_HEADER64, DataDirectory) :
        FIELD_OFFSET(IMAGE_OPTIONAL_HEADER32, DataDirectory);

    dos->e_magic = IMAGE_DOS_SIGNATURE;
    dos->e_lfanew = 128;
    nt->Signature = IMAGE_NT_SIGNATURE;
    nt->OptionalHeader.Magic = Is64 ? IMAGE_NT_OPTIONAL_HDR64_MAGIC : IMAGE_NT_OPTIONAL_HDR32_MAGIC;
    nt->FileHeader.SizeOfOptionalHeader = offset - 1;
    CHECK(!NT_SUCCESS(PhInitializeMappedImage(&image, bytes, 1024)));

    // 声明 16 个目录，但文件头仅容纳一个：仍可打开，越界目录必须拒绝。
    nt->FileHeader.SizeOfOptionalHeader = offset + sizeof(IMAGE_DATA_DIRECTORY);
    if (Is64)
        ((PIMAGE_OPTIONAL_HEADER64)&nt->OptionalHeader)->NumberOfRvaAndSizes = 16;
    else
        ((PIMAGE_OPTIONAL_HEADER32)&nt->OptionalHeader)->NumberOfRvaAndSizes = 16;
    directories = (PIMAGE_DATA_DIRECTORY)((PBYTE)&nt->OptionalHeader + offset);
    directories[0].VirtualAddress = 0x1000;
    directories[0].Size = 4;
    directories[1].VirtualAddress = 0x2000;
    directories[1].Size = 4;
    CHECK(NT_SUCCESS(PhInitializeMappedImage(&image, bytes, 1024)));
    CHECK(NT_SUCCESS(PhGetMappedImageDataDirectory(&image, 0, &directory)));
    CHECK(!NT_SUCCESS(PhGetMappedImageDataDirectory(&image, 1, &directory)));
    CHECK(!NT_SUCCESS(PhGetMappedImageDataDirectory(&image, MAXULONG, &directory)));

    nt->FileHeader.SizeOfOptionalHeader = 0;
    CHECK(!NT_SUCCESS(PhInitializeMappedImage(&image, bytes,
        128 + FIELD_OFFSET(IMAGE_NT_HEADERS, OptionalHeader))));
    PhFree(bytes);
}

static VOID TestExportNames(VOID)
{
    BYTE bytes[1024] = { 0 };
    IMAGE_SECTION_HEADER section = { 0 };
    IMAGE_EXPORT_DIRECTORY directory = { 0 };
    PH_MAPPED_IMAGE image = { 0 };
    PH_MAPPED_IMAGE_EXPORTS exports = { 0 };
    PH_MAPPED_IMAGE_EXPORT_ENTRY entry;
    ULONG nameRva = 0x11fc;
    USHORT ordinal = 0;

    section.VirtualAddress = 0x1000;
    section.PointerToRawData = 512;
    section.SizeOfRawData = 512;
    image.ViewBase = bytes;
    image.ViewSize = sizeof(bytes);
    image.Sections = &section;
    image.NumberOfSections = 1;
    directory.NumberOfFunctions = 1;
    directory.NumberOfNames = 1;
    exports.MappedImage = &image;
    exports.ExportDirectory = &directory;
    exports.NamePointerTable = &nameRva;
    exports.OrdinalTable = &ordinal;

    memcpy(bytes + 1020, "abc", 4);
    CHECK(NT_SUCCESS(PhGetMappedImageExportEntry(&exports, 0, &entry)));
    CHECK(PhLookupMappedImageExportName(&exports, "abc") == 0);
    CHECK(PhLookupMappedImageExportName(&exports, "abd") == MAXULONG);
    bytes[1023] = 'd';
    CHECK(!NT_SUCCESS(PhGetMappedImageExportEntry(&exports, 0, &entry)));
    // 缩短映射后，后面的物理内存仍有 abc\0，也不能将它算作有效名称。
    memcpy(bytes + 1020, "abc", 4);
    image.ViewSize = 1022;
    CHECK(PhLookupMappedImageExportName(&exports, "abc") == MAXULONG);
}

static VOID TestSettingsGrowth(VOID)
{
    static WCHAR names[2048][32];
    PH_STRINGREF name = PH_STRINGREF_INIT(L"BackportCachedSetting");
    PH_STRINGREF value = PH_STRINGREF_INIT(L"1");
    PPH_SETTING cached;

    PhSettingsInitialization();
    PhAddSetting(IntegerSettingType, &name, &value);
    cached = PhGetSetting(&name);
    CHECK(cached != NULL);
    for (ULONG i = 0; i < RTL_NUMBER_OF(names); i++)
    {
        PH_STRINGREF next;
        swprintf_s(names[i], RTL_NUMBER_OF(names[i]), L"BackportSetting%lu", i);
        PhInitializeStringRef(&next, names[i]);
        PhAddSetting(IntegerSettingType, &next, &value);
    }
    CHECK(PhGetSetting(&name) == cached);
    PhSetIntegerSetting(L"BackportCachedSetting", 42);
    CHECK(PhGetIntegerSetting(L"BackportCachedSetting") == 42);
    PhAddSetting(IntegerSettingType, &name, &value);
    CHECK(PhGetIntegerSetting(L"BackportCachedSetting") == 42);
    PhResetSettings(NULL);
    CHECK(PhGetIntegerSetting(L"BackportCachedSetting") == 1);
}

static VOID TestResourceBounds(VOID)
{
    PBYTE bytes = PhAllocateZero(1024);
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)bytes;
    PIMAGE_NT_HEADERS32 nt = (PIMAGE_NT_HEADERS32)(bytes + 128);
    PIMAGE_SECTION_HEADER section;
    PIMAGE_RESOURCE_DATA_ENTRY data = (PIMAGE_RESOURCE_DATA_ENTRY)(bytes + 584);
    PH_MAPPED_IMAGE image;
    PVOID buffer;
    ULONG length;

    dos->e_magic = IMAGE_DOS_SIGNATURE;
    dos->e_lfanew = 128;
    nt->Signature = IMAGE_NT_SIGNATURE;
    nt->FileHeader.SizeOfOptionalHeader = sizeof(IMAGE_OPTIONAL_HEADER32);
    nt->FileHeader.NumberOfSections = 1;
    nt->OptionalHeader.Magic = IMAGE_NT_OPTIONAL_HDR32_MAGIC;
    nt->OptionalHeader.NumberOfRvaAndSizes = 16;
    nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_RESOURCE].VirtualAddress = 0x1000;
    nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_RESOURCE].Size = 88;
    section = IMAGE_FIRST_SECTION(nt);
    section->VirtualAddress = 0x1000;
    section->PointerToRawData = 512;
    section->SizeOfRawData = 512;
    for (ULONG i = 0; i < 3; i++)
    {
        PIMAGE_RESOURCE_DIRECTORY dir = (PIMAGE_RESOURCE_DIRECTORY)(bytes + 512 + i * 24);
        PIMAGE_RESOURCE_DIRECTORY_ENTRY entry = (PIMAGE_RESOURCE_DIRECTORY_ENTRY)(dir + 1);
        dir->NumberOfIdEntries = 1;
        entry->Id = i == 0 ? 16 : (i == 1 ? 1 : 1033);
        entry->OffsetToData = (i + 1) * 24;
        entry->DataIsDirectory = i < 2;
    }
    data->OffsetToData = 0x11fc;
    data->Size = 4;
    CHECK(NT_SUCCESS(PhInitializeMappedImage(&image, bytes, 1024)));
    CHECK(NT_SUCCESS(PhGetMappedImageResource(&image, MAKEINTRESOURCE(1), RT_VERSION, 1033, &length, &buffer)));
    CHECK(length == 4 && buffer == bytes + 1020);
    data->Size = 5;
    length = 123;
    buffer = NULL;
    CHECK(!NT_SUCCESS(PhGetMappedImageResource(&image, MAKEINTRESOURCE(1), RT_VERSION, 1033, &length, &buffer)));
    CHECK(length == 123 && buffer == NULL);
    CHECK(!NT_SUCCESS(PhGetMappedImageResourceBinarySearch(&image, MAKEINTRESOURCE(1), RT_VERSION, 1033, &length, &buffer)));
    PhFree(bytes);
}

static VOID TestEmptyFileQuery(VOID)
{
    WCHAR temp[MAX_PATH];
    WCHAR path[MAX_PATH];
    HANDLE handle;
    PVOID streams = NULL;
    NTSTATUS status;
    DWORD length = GetTempPath(RTL_NUMBER_OF(temp), temp);

    CHECK(length > 0 && length < RTL_NUMBER_OF(temp));
    if (!length || length >= RTL_NUMBER_OF(temp))
        return;
    if (swprintf_s(path, RTL_NUMBER_OF(path), L"%sphlib-backport-%lu-%llu",
        temp, GetCurrentProcessId(), GetTickCount64()) < 0)
    {
        CHECK(FALSE);
        return;
    }
    // 每次测试独占一个空目录，不读取或清理用户文件。
    if (!CreateDirectory(path, NULL))
    {
        CHECK(FALSE);
        return;
    }
    handle = CreateFile(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
    CHECK(handle != INVALID_HANDLE_VALUE);
    if (handle != INVALID_HANDLE_VALUE)
    {
        status = PhEnumFileStreams(handle, &streams);
        CHECK(status == STATUS_NO_MORE_ENTRIES);
        CHECK(streams == NULL);
        if (streams)
            PhFree(streams);
        CloseHandle(handle);
    }
    CHECK(RemoveDirectory(path));
}

VOID Test_backports(VOID)
{
    TestOptionalHeader(FALSE);
    TestOptionalHeader(TRUE);
    TestExportNames();
    TestResourceBounds();
    TestEmptyFileQuery();
    TestSettingsGrowth();
    printf("Backport regressions: %lu failures\n", Failures);
    fflush(stdout);
    if (Failures)
        exit(1);
}
