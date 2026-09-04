/*
 * Community edition translation layer (zh-CN).
 *
 * This file is part of the System Informer Simplified Chinese community
 * edition. It provides the runtime English->Chinese dictionary used by the
 * UI helper funnels in phlib; see phtranslation.h for details.
 */

#include <ph.h>
#include <phtranslation.h>
#include <mapldr.h>

#include <wchar.h>

BOOLEAN PhTranslationEnabled = TRUE;

extern const PH_TRANSLATION_ENTRY PhTranslationTableZhCn[];
extern const ULONG PhTranslationTableZhCnCount;

/**
 * Looks up the translation of an English source string.
 *
 * \param English The English source string.
 * \return The Chinese translation, or \a English when translation is
 * disabled or the string has no entry.
 */
PCWSTR PhTranslateString(
    _In_opt_ PCWSTR English
    )
{
    ULONG low;
    ULONG high;

    if (!PhTranslationEnabled || !English)
        return English;

    // The table is sorted by ordinal UTF-16 code unit order to match wcscmp.
    low = 0;
    high = PhTranslationTableZhCnCount;

    while (low < high)
    {
        ULONG middle = low + (high - low) / 2;
        INT comparison = wcscmp(English, PhTranslationTableZhCn[middle].English);

        if (comparison == 0)
            return PhTranslationTableZhCn[middle].Chinese;
        if (comparison < 0)
            high = middle;
        else
            low = middle + 1;
    }

    return English;
}

//
// Dialog template translation.
//
// Dialog and property-sheet page texts live in DLGTEMPLATE resources. The
// helpers below rebuild a template with every translatable string (the
// caption and each control's text) replaced by its dictionary entry,
// copying everything else verbatim. Windows then creates the dialog from
// the translated copy, so no dialog procedure or creation parameter is
// touched. Templates are cached per (module, resource name) because a
// translated copy stays valid for the lifetime of the process.
//

typedef struct _PH_TL_WRITER
{
    PBYTE Buffer;
    SIZE_T Used;
    SIZE_T Allocated;
    BOOLEAN Failed;
} PH_TL_WRITER, *PPH_TL_WRITER;

static VOID PhTlpReserve(
    _Inout_ PPH_TL_WRITER Writer,
    _In_ SIZE_T Size
    )
{
    if (Writer->Failed)
        return;

    if (Writer->Used + Size > Writer->Allocated)
    {
        SIZE_T newAllocated;
        PBYTE newBuffer;

        newAllocated = Writer->Allocated ? Writer->Allocated * 2 : 512;

        while (newAllocated < Writer->Used + Size)
            newAllocated *= 2;

        newBuffer = PhReAllocate(Writer->Buffer, newAllocated);

        if (!newBuffer)
        {
            Writer->Failed = TRUE;
            return;
        }

        Writer->Buffer = newBuffer;
        Writer->Allocated = newAllocated;
    }
}

static VOID PhTlpWrite(
    _Inout_ PPH_TL_WRITER Writer,
    _In_ PVOID Data,
    _In_ SIZE_T Size
    )
{
    PhTlpReserve(Writer, Size);

    if (Writer->Failed)
        return;

    memcpy(Writer->Buffer + Writer->Used, Data, Size);
    Writer->Used += Size;
}

static VOID PhTlpWriteWord(
    _Inout_ PPH_TL_WRITER Writer,
    _In_ USHORT Value
    )
{
    PhTlpWrite(Writer, &Value, sizeof(USHORT));
}

static VOID PhTlpPadToDword(
    _Inout_ PPH_TL_WRITER Writer
    )
{
    while (Writer->Used & 3)
        PhTlpWriteWord(Writer, 0);
}

/**
 * Copies a template string, replacing it with its translation when one
 * exists. Template strings are either a single 0xFFFF ordinal marker
 * followed by an ordinal WORD, or a null-terminated wchar string.
 *
 * \param Writer The destination writer.
 * \param Cursor On input the string position in the source; on output
 * advanced past the string.
 * \param Translate TRUE to look the string up in the dictionary.
 * \param Changed Optional flag set when a translation was written.
 */
static VOID PhTlpWriteTemplateString(
    _Inout_ PPH_TL_WRITER Writer,
    _Inout_ PBYTE *Cursor,
    _In_ BOOLEAN Translate,
    _Inout_opt_ PBOOLEAN Changed
    )
{
    PCWSTR source;
    PCWSTR translated;
    SIZE_T length;

    if (*(PUSHORT)*Cursor == 0xFFFF)
    {
        PhTlpWrite(Writer, *Cursor, 2 * sizeof(USHORT));
        *Cursor += 2 * sizeof(USHORT);
        return;
    }

    source = (PCWSTR)*Cursor;
    length = wcslen(source);
    translated = Translate ? PhTranslateString(source) : source;

    if (Changed && translated != source)
        *Changed = TRUE;

    PhTlpWrite(Writer, (PVOID)translated, (length + 1) * sizeof(WCHAR));
    *Cursor += (length + 1) * sizeof(WCHAR);
}

/**
 * Copies a template string of known byte length verbatim.
 */
static VOID PhTlpCopyTemplateString(
    _Inout_ PPH_TL_WRITER Writer,
    _Inout_ PBYTE *Cursor
    )
{
    PCWSTR source;
    SIZE_T length;

    if (*(PUSHORT)*Cursor == 0xFFFF)
    {
        PhTlpWrite(Writer, *Cursor, 2 * sizeof(USHORT));
        *Cursor += 2 * sizeof(USHORT);
        return;
    }

    source = (PCWSTR)*Cursor;
    length = wcslen(source);
    PhTlpWrite(Writer, (PVOID)source, (length + 1) * sizeof(WCHAR));
    *Cursor += (length + 1) * sizeof(WCHAR);
}

/**
 * Rebuilds a dialog template with translated caption and control texts.
 *
 * \param Template The original DLGTEMPLATE or DLGTEMPLATEEX.
 * \return An allocated translated copy, or NULL when translation is
 * disabled or an allocation failed.
 */
PVOID PhTranslateDialogTemplateCopy(
    _In_ PVOID Template
    )
{
    PH_TL_WRITER writer;
    PBYTE cursor;
    ULONG headerSize;
    USHORT itemCount;
    ULONG extended;
    ULONG i;
    BOOLEAN changed;

    if (!PhTranslationEnabled)
        return NULL;

    memset(&writer, 0, sizeof(writer));
    changed = FALSE;

    cursor = (PBYTE)Template;

    // DLGTEMPLATEEX as emitted by rc.exe: version(2) signature(2) helpID(4)
    // exStyle(4) style(4) cdit(2) x(2) y(2) cx(2) cy(2); the signature word
    // (0xFFFF) is at offset 2, and there is no cDlgPages field.
    extended = ((PUSHORT)cursor)[1] == USHRT_MAX;

    if (extended)
    {
        itemCount = *(PUSHORT)(cursor + 16);
        headerSize = 26;
    }
    else
    {
        // DLGTEMPLATE: style(4) dwExtendedStyle(4) cdit(2) x(2) y(2) cx(2) cy(2)
        itemCount = *(PUSHORT)(cursor + 8);
        headerSize = 18;
    }

    PhTlpWrite(&writer, (PVOID)cursor, headerSize);
    cursor += headerSize;

    // menu, class (copied verbatim), title (translated)
    PhTlpCopyTemplateString(&writer, &cursor);
    PhTlpCopyTemplateString(&writer, &cursor);
    PhTlpWriteTemplateString(&writer, &cursor, TRUE, &changed);

    if (*(PULONG)((PBYTE)Template + (extended ? 12 : 0)) & (DS_SETFONT | DS_SHELLFONT))
    {
        if (extended)
        {
            // pointsize(2) weight(2) italic(1) charset(1) typeface(string);
            // substitute the Windows zh-CN standard UI font so Chinese text
            // renders crisp instead of falling back from MS Shell Dlg 8pt.
            USHORT pointSize = *(PUSHORT)cursor;
            USHORT weight = *(PUSHORT)(cursor + 2);

            if (pointSize < 9)
                pointSize = 9;

            PhTlpWriteWord(&writer, pointSize);
            PhTlpWriteWord(&writer, weight);
            PhTlpWrite(&writer, (PVOID)(cursor + 4), 2); // italic + charset
            cursor += 6;
        }
        else
        {
            USHORT pointSize = *(PUSHORT)cursor;

            if (pointSize < 9)
                pointSize = 9;

            PhTlpWriteWord(&writer, pointSize);
            cursor += 2;
        }

        // skip the original typeface (wide characters)
        while (*(PUSHORT)cursor != 0)
            cursor += sizeof(WCHAR);
        cursor += sizeof(WCHAR);
        {
            static const WCHAR zhCnFont[] = L"Microsoft YaHei UI";

            PhTlpWrite(&writer, (PVOID)zhCnFont, (wcslen(zhCnFont) + 1) * sizeof(WCHAR));
        }
        PhTlpWriteWord(&writer, 0);
        changed = TRUE;
    }

    PhTlpPadToDword(&writer);

    for (i = 0; i < itemCount; i++)
    {
        ULONG itemHeaderSize;

        // advance the source cursor to the next DWORD boundary
        while ((ULONG_PTR)cursor & 3)
            cursor++;

        itemHeaderSize = extended ? 24 : 18;
        PhTlpWrite(&writer, (PVOID)cursor, itemHeaderSize);
        cursor += itemHeaderSize;

        PhTlpCopyTemplateString(&writer, &cursor); // class
        PhTlpWriteTemplateString(&writer, &cursor, TRUE, &changed); // text

        // creation data: size WORD followed by that many bytes
        {
            USHORT creationSize = *(PUSHORT)cursor;
            PhTlpWrite(&writer, (PVOID)cursor, sizeof(USHORT) + creationSize);
            cursor += sizeof(USHORT) + creationSize;
        }

        PhTlpPadToDword(&writer);
    }

    if (writer.Failed || !changed)
    {
        if (writer.Buffer)
            PhFree(writer.Buffer);

        return NULL;
    }

    return writer.Buffer;
}

/**
 * Translates the caption and child control texts of a window when they have
 * dictionary entries. This is the second translation layer for dialogs: it
 * runs on the created window, so static texts are localized even when the
 * translated dialog-template path is bypassed or rejected. Controls holding
 * dynamic data never match the dictionary and keep their text.
 */
static BOOL CALLBACK PhTlpEnumChildProc(
    _In_ HWND WindowHandle,
    _In_ LPARAM UnusedParameter
    )
{
    WCHAR buffer[256];
    PCWSTR translated;

    UNREFERENCED_PARAMETER(UnusedParameter);

    if (GetWindowText(WindowHandle, buffer, ARRAYSIZE(buffer)))
    {
        translated = PhTranslateString(buffer);

        if (translated != buffer)
            SetWindowText(WindowHandle, translated);
    }

    return TRUE;
}

VOID PhTranslateWindowTree(
    _In_ HWND WindowHandle
    )
{
    WCHAR buffer[256];
    PCWSTR translated;

    if (!PhTranslationEnabled)
        return;

    if (GetWindowText(WindowHandle, buffer, ARRAYSIZE(buffer)))
    {
        translated = PhTranslateString(buffer);

        if (translated != buffer)
            SetWindowText(WindowHandle, translated);
    }

    EnumChildWindows(WindowHandle, PhTlpEnumChildProc, 0);
}

static HHOOK PhTlModalDialogHook;

/**
 * CBT hook installed around DialogBoxIndirectParam: translates the modal
 * dialog when it is first activated, covering texts set after creation as
 * well as template texts.
 */
static LRESULT CALLBACK PhTlpModalDialogCbtProc(
    _In_ INT Code,
    _In_ WPARAM WParam,
    _In_ LPARAM LParam
    )
{
    if (Code == HCBT_ACTIVATE)
    {
        PhTranslateWindowTree((HWND)WParam);
        return CallNextHookEx(NULL, Code, WParam, LParam);
    }

    return CallNextHookEx(NULL, Code, WParam, LParam);
}

VOID PhTranslateModalDialogBegin(VOID)
{
    if (!PhTranslationEnabled)
        return;

    PhTlModalDialogHook = SetWindowsHookEx(
        WH_CBT,
        PhTlpModalDialogCbtProc,
        NULL,
        GetCurrentThreadId()
        );
}

VOID PhTranslateModalDialogEnd(VOID)
{
    if (PhTlModalDialogHook)
    {
        UnhookWindowsHookEx(PhTlModalDialogHook);
        PhTlModalDialogHook = NULL;
    }
}

//
// Process-lifetime cache of translated templates, keyed by module and
// resource name. Property sheet pages reference the cached copy via
// PSP_DLGINDIRECT, which requires the buffer to stay valid while the page
// exists.
//

typedef struct _PH_TL_CACHE_ENTRY
{
    PVOID Instance;
    PCWSTR Template;
    PVOID Translated;
} PH_TL_CACHE_ENTRY, *PPH_TL_CACHE_ENTRY;

#define PH_TL_CACHE_CAPACITY 256

static PH_TL_CACHE_ENTRY PhTlTemplateCache[PH_TL_CACHE_CAPACITY];
static ULONG PhTlTemplateCacheCount;
static PH_QUEUED_LOCK PhTlTemplateCacheLock = PH_QUEUED_LOCK_INIT;

/**
 * Returns a cached translated copy of a dialog template resource.
 *
 * \param Instance The module containing the template.
 * \param Template The dialog resource name.
 * \param Translated Receives TRUE when a translated copy was produced.
 * \return The translated copy, or the original resource pointer when the
 * template has nothing to translate.
 */
PVOID PhTranslateDialogTemplateCached(
    _In_ PVOID Instance,
    _In_ PCWSTR Template,
    _Out_opt_ PBOOLEAN Translated
    )
{
    PVOID resource;
    PPH_TL_CACHE_ENTRY entry;
    PVOID result;
    ULONG i;

    if (Translated)
        *Translated = FALSE;

    if (!PhTranslationEnabled)
    {
        if (NT_SUCCESS(PhLoadResource(Instance, Template, RT_DIALOG, NULL, &resource)))
            return resource;

        return NULL;
    }

    PhAcquireQueuedLockExclusive(&PhTlTemplateCacheLock);

    for (i = 0; i < PhTlTemplateCacheCount; i++)
    {
        entry = &PhTlTemplateCache[i];

        if (entry->Instance == Instance && entry->Template == Template)
        {
            result = entry->Translated;

            if (result && Translated)
                *Translated = TRUE;

            PhReleaseQueuedLockExclusive(&PhTlTemplateCacheLock);
            return result;
        }
    }

    PhReleaseQueuedLockExclusive(&PhTlTemplateCacheLock);

    if (!NT_SUCCESS(PhLoadResource(Instance, Template, RT_DIALOG, NULL, &resource)))
        return NULL;

    result = PhTranslateDialogTemplateCopy(resource);

    if (!result)
        return resource; // nothing to translate; the resource pointer stays valid

    PhAcquireQueuedLockExclusive(&PhTlTemplateCacheLock);

    if (PhTlTemplateCacheCount < PH_TL_CACHE_CAPACITY)
    {
        entry = &PhTlTemplateCache[PhTlTemplateCacheCount++];
        entry->Instance = Instance;
        entry->Template = Template;
        entry->Translated = result;
    }

    PhReleaseQueuedLockExclusive(&PhTlTemplateCacheLock);

    if (Translated)
        *Translated = TRUE;

    return result;
}
