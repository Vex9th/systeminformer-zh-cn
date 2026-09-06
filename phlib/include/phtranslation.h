#ifndef PH_PHTRANSLATION_H
#define PH_PHTRANSLATION_H

#ifdef __cplusplus
extern "C" {
#endif

// Community edition translation layer (zh-CN).
//
// PhTranslateString performs a dictionary lookup of an English source string
// and returns the Simplified Chinese translation, or the input unchanged when
// no translation exists. All UI helper funnels in phlib (extended menus, list
// view and treenew columns, message boxes and task dialogs, tab controls and
// notification banners) route their static text
// through this function, which also covers plugins because they share these
// exports.
//
// Missing translations fall back to English, so strings introduced by future
// upstream merges are displayed in English until the table is updated.

typedef struct _PH_TRANSLATION_ENTRY
{
    PCWSTR English;
    PCWSTR Chinese;
} PH_TRANSLATION_ENTRY, *PPH_TRANSLATION_ENTRY;

/**
 * Controls dictionary lookups. FALSE until the application explicitly
 * selects zh-CN after loading settings.
 */
extern BOOLEAN PhTranslationEnabled;

/**
 * Looks up the translation of an English source string.
 *
 * \param English The English source string.
 * \return The Chinese translation, or \a English when translation is
 * disabled or the string has no entry. The returned pointer is either the
 * input itself or a pointer into a static table and is valid indefinitely.
 */
PHLIBAPI PCWSTR PhTranslateString(
    _In_opt_ PCWSTR English
    );

#ifdef __cplusplus
}
#endif

#endif // PH_PHTRANSLATION_H
