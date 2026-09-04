/* Native UI resource loader regression tests. */

#include "tests.h"
#include "resource.h"

#include <guisup.h>
#include <mapldr.h>
#include <phtranslation.h>
#include <stdlib.h>
#include <wchar.h>

typedef struct _PH_UI_RESOURCE_TEST_CONTEXT
{
    PCWSTR Caption;
    PCWSTR Label;
    BOOLEAN EndModal;
    BOOLEAN Verified;
} PH_UI_RESOURCE_TEST_CONTEXT, *PPH_UI_RESOURCE_TEST_CONTEXT;

static VOID TestRequire(
    _In_ BOOLEAN Condition
    )
{
    if (!Condition)
        abort();
}

static INT_PTR CALLBACK TestResourceDialogProc(
    _In_ HWND WindowHandle,
    _In_ UINT Message,
    _In_ WPARAM WParam,
    _In_ LPARAM LParam
    )
{
    PPH_UI_RESOURCE_TEST_CONTEXT context;
    WCHAR caption[64];
    WCHAR label[64];

    UNREFERENCED_PARAMETER(WParam);

    if (Message != WM_INITDIALOG)
        return FALSE;

    context = (PPH_UI_RESOURCE_TEST_CONTEXT)LParam;
    GetWindowText(WindowHandle, caption, RTL_NUMBER_OF(caption));
    GetDlgItemText(WindowHandle, IDC_UI_RESOURCE_LABEL, label, RTL_NUMBER_OF(label));

    context->Verified =
        wcscmp(caption, context->Caption) == 0 &&
        wcscmp(label, context->Label) == 0;

    if (context->EndModal)
        EndDialog(WindowHandle, IDOK);

    return TRUE;
}

static INT_PTR CALLBACK TestResourcePageProc(
    _In_ HWND WindowHandle,
    _In_ UINT Message,
    _In_ WPARAM WParam,
    _In_ LPARAM LParam
    )
{
    LPPROPSHEETPAGE page;
    PPH_UI_RESOURCE_TEST_CONTEXT context;
    WCHAR caption[64];
    WCHAR label[64];

    UNREFERENCED_PARAMETER(WParam);

    if (Message != WM_INITDIALOG)
        return FALSE;

    page = (LPPROPSHEETPAGE)LParam;
    context = (PPH_UI_RESOURCE_TEST_CONTEXT)page->lParam;
    GetWindowText(WindowHandle, caption, RTL_NUMBER_OF(caption));
    GetDlgItemText(WindowHandle, IDC_UI_RESOURCE_LABEL, label, RTL_NUMBER_OF(label));

    context->Verified =
        wcscmp(caption, context->Caption) == 0 &&
        wcscmp(label, context->Label) == 0;

    TestRequire(PostMessage(
        GetParent(WindowHandle),
        PSM_PRESSBUTTON,
        PSBTN_CANCEL,
        0
        ));

    return TRUE;
}

static VOID TestDialogResources(
    _In_ PVOID ImageBase,
    _In_ LANGID LanguageId,
    _In_ PCWSTR ExpectedCaption,
    _In_ PCWSTR ExpectedLabel,
    _In_ PCWSTR ExpectedPageCaption,
    _In_ PCWSTR ExpectedPageLabel
    )
{
    PH_UI_RESOURCE_TEST_CONTEXT context;
    PROPSHEETPAGE page;
    PROPSHEETHEADER header;
    HPROPSHEETPAGE pageHandle;
    HWND dialogHandle;
    INT_PTR dialogResult;
    INT_PTR propertySheetResult;

    PhSetApplicationUiLanguage(LanguageId);

    memset(&context, 0, sizeof(context));
    context.Caption = ExpectedCaption;
    context.Label = ExpectedLabel;
    dialogHandle = PhCreateDialog(
        ImageBase,
        MAKEINTRESOURCE(IDD_UI_RESOURCE_TEST),
        NULL,
        TestResourceDialogProc,
        &context
        );
    TestRequire(dialogHandle && context.Verified);
    DestroyWindow(dialogHandle);

    memset(&context, 0, sizeof(context));
    context.Caption = ExpectedCaption;
    context.Label = ExpectedLabel;
    context.EndModal = TRUE;
    dialogResult = PhDialogBox(
        ImageBase,
        MAKEINTRESOURCE(IDD_UI_RESOURCE_TEST),
        NULL,
        TestResourceDialogProc,
        &context
        );
    TestRequire(dialogResult == IDOK && context.Verified);

    memset(&page, 0, sizeof(page));
    page.dwSize = sizeof(page);
    page.hInstance = ImageBase;
    page.pszTemplate = MAKEINTRESOURCE(IDD_UI_RESOURCE_PAGE_TEST);
    page.pfnDlgProc = TestResourcePageProc;
    context.Caption = ExpectedPageCaption;
    context.Label = ExpectedPageLabel;
    context.Verified = FALSE;
    page.lParam = (LPARAM)&context;
    pageHandle = PhCreatePropertySheetPage(&page);
    TestRequire(!!pageHandle);

    memset(&header, 0, sizeof(header));
    header.dwSize = sizeof(header);
    header.dwFlags = PSH_NOAPPLYNOW | PSH_NOCONTEXTHELP;
    header.hInstance = ImageBase;
    header.pszCaption = L"UI resource test";
    header.nPages = 1;
    header.phpage = &pageHandle;
    propertySheetResult = PropertySheet(&header);
    TestRequire(propertySheetResult != -1 && context.Verified);
}

static VOID TestMenuResource(
    _In_ PVOID ImageBase,
    _In_ LANGID LanguageId,
    _In_ PCWSTR ExpectedText
    )
{
    WCHAR text[64];
    HMENU menuHandle;

    PhSetApplicationUiLanguage(LanguageId);
    menuHandle = PhLoadMenu(ImageBase, MAKEINTRESOURCE(IDM_UI_RESOURCE_TEST));
    TestRequire(!!menuHandle);
    TestRequire(GetMenuString(
        menuHandle,
        0,
        text,
        RTL_NUMBER_OF(text),
        MF_BYPOSITION
        ) > 0);
    TestRequire(wcscmp(text, ExpectedText) == 0);
    DestroyMenu(menuHandle);
}

static VOID TestLegacyTranslatedDialog(
    _In_ PVOID ImageBase
    )
{
    PH_UI_RESOURCE_TEST_CONTEXT context;
    HWND dialogHandle;

    memset(&context, 0, sizeof(context));
    context.Caption = L"\x5E38\x89C4";
    context.Label = L"\x8BBE\x7F6E";

    PhSetApplicationUiLanguage(
        MAKELANGID(LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED)
        );
    PhTranslationEnabled = TRUE;
    dialogHandle = PhCreateDialog(
        ImageBase,
        MAKEINTRESOURCE(IDD_UI_RESOURCE_LEGACY_TEST),
        NULL,
        TestResourceDialogProc,
        &context
        );
    PhTranslationEnabled = FALSE;

    TestRequire(dialogHandle && context.Verified);
    DestroyWindow(dialogHandle);
}

VOID Test_resource(
    VOID
    )
{
    PVOID imageBase;
    PPH_STRING string;
    BOOLEAN fallbackToEnglish;

    imageBase = NtCurrentPeb()->ImageBaseAddress;

    PhSetApplicationUiLanguage(
        MAKELANGID(LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED)
        );
    string = PhLoadUiString(imageBase, IDS_UI_RESOURCE_TEST, &fallbackToEnglish);
    TestRequire(string && PhEqualString2(string, L"中文资源", FALSE));
    TestRequire(!fallbackToEnglish);
    PhDereferenceObject(string);

    string = PhLoadUiString(imageBase, IDS_UI_RESOURCE_ENGLISH_ONLY, &fallbackToEnglish);
    TestRequire(string && PhEqualString2(string, L"English only", FALSE));
    TestRequire(fallbackToEnglish);
    PhDereferenceObject(string);

    TestDialogResources(
        imageBase,
        MAKELANGID(LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED),
        L"\x4E2D\x6587\x5BF9\x8BDD\x6846",
        L"\x4E2D\x6587\x6807\x7B7E",
        L"\x4E2D\x6587\x5C5E\x6027\x9875",
        L"\x4E2D\x6587\x5C5E\x6027\x9875\x6807\x7B7E"
        );
    TestMenuResource(
        imageBase,
        MAKELANGID(LANG_CHINESE, SUBLANG_CHINESE_SIMPLIFIED),
        L"\x4E2D\x6587\x83DC\x5355"
        );
    TestLegacyTranslatedDialog(imageBase);

    PhSetApplicationUiLanguage(
        MAKELANGID(LANG_JAPANESE, SUBLANG_DEFAULT)
        );
    string = PhLoadUiString(imageBase, IDS_UI_RESOURCE_TEST, &fallbackToEnglish);
    TestRequire(string && PhEqualString2(string, L"English resource", FALSE));
    TestRequire(fallbackToEnglish);
    PhDereferenceObject(string);

    TestDialogResources(
        imageBase,
        MAKELANGID(LANG_JAPANESE, SUBLANG_DEFAULT),
        L"English dialog",
        L"English label",
        L"English page",
        L"English page label"
        );
    TestMenuResource(
        imageBase,
        MAKELANGID(LANG_JAPANESE, SUBLANG_DEFAULT),
        L"English menu"
        );

    PhSetApplicationUiLanguage(
        MAKELANGID(LANG_ENGLISH, SUBLANG_ENGLISH_US)
        );
    string = PhLoadUiString(imageBase, IDS_UI_RESOURCE_TEST, &fallbackToEnglish);
    TestRequire(string && PhEqualString2(string, L"English resource", FALSE));
    TestRequire(!fallbackToEnglish);
    PhDereferenceObject(string);
}
