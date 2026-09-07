/*
 * Compatibility shim for the retired runtime translation API.
 */

#include <ph.h>
#include <phtranslation.h>

/**
 * Returns the caller-provided string unchanged.
 *
 * \remarks The export remains for third-party binary compatibility. UI text
 * is localized through native language resources.
 */
PCWSTR PhTranslateString(
    _In_opt_ PCWSTR English
    )
{
    return English;
}
