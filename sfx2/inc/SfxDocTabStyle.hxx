/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#ifndef INCLUDED_SFX2_SOURCE_INC_SFXDOCTABSTYLE_HXX
#define INCLUDED_SFX2_SOURCE_INC_SFXDOCTABSTYLE_HXX

#include <sal/config.h>

#include <rtl/ustring.hxx>
#include <string_view>

/**
 * Clamp-on-read normalizer for all persisted Material document-tab
 * configuration (the Common.xcs Appearance/DocumentTabs group and the
 * History/DocumentTabStyles set, node-type DocumentTabStyle).
 *
 * This mirrors desktop-material's normalizeTabTitleStyle posture
 * (app/src/models/repository-tab.ts): the on-disk registry is untrusted
 * persisted state, so every value is validated the moment it is read --
 * hex-only colours, an allow-listed font family, a bounded font size, closed
 * enumerations and closed booleans. A hand-edited registry can therefore never
 * inject an unsafe or out-of-range style.
 *
 * The design is fail-closed: an unrecognised, malformed or out-of-range value
 * is replaced by the property's safe default rather than propagated. There is
 * exactly one branch per officecfg property; the build-free contract
 * bin/check-doc-tab-style-schema.py cross-validates that this stays true.
 *
 * Runtime verification is tracked separately from this normalizer's source
 * contract.
 */
class SfxDocTabStyle
{
public:
    /** The outcome of normalizing a single property value. */
    struct Result
    {
        /** true when the value is retained (possibly clamped); false when it
         *  is dropped and the caller must fall back to the schema default. */
        bool bKeep;
        /** The clamped/validated value, valid only when bKeep is true. */
        OUString aValue;
    };

    /** Supported font-size bounds, joined to the FontSize constraint in the
     *  Common.xcs DocumentTabStyle template. */
    static constexpr sal_Int16 MIN_FONT_SIZE = 10;
    static constexpr sal_Int16 MAX_FONT_SIZE = 32;
    static constexpr sal_Int16 DEFAULT_FONT_SIZE = 13;

    /** Longest accepted custom label; longer labels are truncated. */
    static constexpr sal_Int32 MAX_CUSTOM_LABEL_LENGTH = 64;

    /**
     * Normalize a single persisted document-tab configuration value by its
     * officecfg property name. Exactly one branch handles each property.
     *
     * @param rsKey  the officecfg property name (e.g. u"FontSize").
     * @param rsRaw  the untrusted persisted value, serialized as a string.
     * @return the clamp result; bKeep==false means "use the schema default".
     */
    static Result Normalize(std::u16string_view rsKey, const OUString& rsRaw);

    /** Only #rgb / #rrggbb / #rrggbbaa hex colours are safe for inline use. */
    static bool IsValidHexColor(const OUString& rColor);

    /** Allow-listed font family: a leading alphanumeric then alphanumerics,
     *  spaces and hyphens, bounded length. Mirrors the desktop-material
     *  fontFamilyPattern /^[a-z0-9][a-z0-9 -]{0,63}$/i. */
    static bool IsValidFontFamily(const OUString& rFamily);

    /** Allow-listed group id: same shape as a font family token. */
    static bool IsValidGroupId(const OUString& rGroupId);
};

#endif // INCLUDED_SFX2_SOURCE_INC_SFXDOCTABSTYLE_HXX

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
