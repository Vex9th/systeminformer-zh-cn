/*
 * Community edition translation layer (zh-CN).
 *
 * This file is part of the System Informer Simplified Chinese community
 * edition. It provides the runtime English->Chinese dictionary used by the
 * UI helper funnels in phlib; see phtranslation.h for details.
 */

#include <ph.h>
#include <phtranslation.h>

#include <wchar.h>

BOOLEAN PhTranslationEnabled = FALSE;

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

    if (
        !PhTranslationEnabled ||
        !English ||
        IS_INTRESOURCE(English) ||
        (ULONG_PTR)English == MAXULONG_PTR
        )
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
