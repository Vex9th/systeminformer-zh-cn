#ifndef PH_PHTRANSLATION_H
#define PH_PHTRANSLATION_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Returns the caller-provided string unchanged.
 *
 * \remarks Retained only for third-party binary compatibility after the
 * runtime dictionary was replaced by native language resources.
 */
PHLIBAPI PCWSTR PhTranslateString(
    _In_opt_ PCWSTR English
    );

#ifdef __cplusplus
}
#endif

#endif // PH_PHTRANSLATION_H
