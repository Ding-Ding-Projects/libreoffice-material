/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <SfxDocTabStyle.hxx>

#include <rtl/ustrbuf.hxx>
#include <sal/types.h>

/*
 * Clamp-on-read normalizer for persisted Material document-tab configuration.
 *
 * Ported from desktop-material's normalizeTabTitleStyle
 * (app/src/models/repository-tab.ts). One branch per officecfg property; the
 * fail-closed contract bin/check-doc-tab-style-schema.py pins the branch set to
 * the schema property set in both directions.
 */

namespace
{
// Clamp posture helpers -----------------------------------------------------

/** Parse a signed integer, reporting success separately from the value so a
 *  malformed value can fail closed rather than silently reading as 0. */
bool parseInt(const OUString& rsRaw, sal_Int64& rnOut)
{
    if (rsRaw.isEmpty())
        return false;
    sal_Int32 nEnd = 0;
    const sal_Int64 nVal = rsRaw.toInt64();
    // toInt64 returns 0 both for "0" and for junk; re-serialize to confirm the
    // input was a clean integer token.
    (void)nEnd;
    OUString aRound = OUString::number(nVal);
    if (aRound == rsRaw.trim())
    {
        rnOut = nVal;
        return true;
    }
    return false;
}

/** A closed boolean: only the exact tokens "true"/"false" are accepted. */
SfxDocTabStyle::Result normalizeBool(const OUString& rsRaw)
{
    if (rsRaw == u"true" || rsRaw == u"false")
        return { true, rsRaw };
    return { false, OUString() };
}

/** A closed short enumeration in [0, nMax]. */
SfxDocTabStyle::Result normalizeEnum(const OUString& rsRaw, sal_Int64 nMax)
{
    sal_Int64 nVal = 0;
    if (parseInt(rsRaw, nVal) && nVal >= 0 && nVal <= nMax)
        return { true, OUString::number(nVal) };
    return { false, OUString() };
}
}

bool SfxDocTabStyle::IsValidHexColor(const OUString& rColor)
{
    const sal_Int32 nLen = rColor.getLength();
    if (nLen == 0 || rColor[0] != '#')
        return false;
    const sal_Int32 nDigits = nLen - 1;
    if (nDigits != 3 && nDigits != 6 && nDigits != 8)
        return false;
    for (sal_Int32 i = 1; i < nLen; ++i)
    {
        const sal_Unicode c = rColor[i];
        const bool bHex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')
                          || (c >= 'A' && c <= 'F');
        if (!bHex)
            return false;
    }
    return true;
}

bool SfxDocTabStyle::IsValidFontFamily(const OUString& rFamily)
{
    // /^[a-z0-9][a-z0-9 -]{0,63}$/i
    const sal_Int32 nLen = rFamily.getLength();
    if (nLen == 0 || nLen > 64)
        return false;
    for (sal_Int32 i = 0; i < nLen; ++i)
    {
        const sal_Unicode c = rFamily[i];
        const bool bAlnum = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z')
                            || (c >= 'A' && c <= 'Z');
        if (i == 0)
        {
            if (!bAlnum)
                return false;
        }
        else if (!bAlnum && c != ' ' && c != '-')
        {
            return false;
        }
    }
    return true;
}

bool SfxDocTabStyle::IsValidGroupId(const OUString& rGroupId)
{
    // Group ids share the font-family token shape: a bounded allow-list so an
    // untrusted id can never carry markup or path separators.
    return IsValidFontFamily(rGroupId);
}

SfxDocTabStyle::Result SfxDocTabStyle::Normalize(std::u16string_view rsKey,
                                                 const OUString& rsRaw)
{
    // --- Appearance/DocumentTabs group (app-level strip settings) ---------
    if (rsKey == u"TabsEnabled")
    {
        // Fail-closed default is false; only a clean boolean is retained.
        return normalizeBool(rsRaw);
    }
    if (rsKey == u"TabWidth")
    {
        // compact(0) / standard(1) / wide(2)
        return normalizeEnum(rsRaw, 2);
    }
    if (rsKey == u"TabCloseButtons")
    {
        // hover(0) / always(1) / active(2)
        return normalizeEnum(rsRaw, 2);
    }
    if (rsKey == u"TabDensity")
    {
        // comfortable(0) / compact(1), joined to Appearance/MaterialDensity
        return normalizeEnum(rsRaw, 1);
    }

    // --- Histories/DocumentTabStyles per-document style -------------------
    if (rsKey == u"CustomLabel")
    {
        // Collapse whitespace, trim, and bound the length; empty is dropped.
        OUStringBuffer aBuf(rsRaw.getLength());
        bool bPrevSpace = false;
        for (sal_Int32 i = 0; i < rsRaw.getLength(); ++i)
        {
            const sal_Unicode c = rsRaw[i];
            const bool bSpace = (c == ' ' || c == '\t' || c == '\n' || c == '\r');
            if (bSpace)
            {
                if (!bPrevSpace)
                    aBuf.append(' ');
                bPrevSpace = true;
            }
            else
            {
                aBuf.append(c);
                bPrevSpace = false;
            }
        }
        OUString aTrimmed = aBuf.makeStringAndClear().trim();
        if (aTrimmed.isEmpty())
            return { false, OUString() };
        if (aTrimmed.getLength() > MAX_CUSTOM_LABEL_LENGTH)
            aTrimmed = aTrimmed.copy(0, MAX_CUSTOM_LABEL_LENGTH);
        return { true, aTrimmed };
    }
    if (rsKey == u"Pinned")
    {
        return normalizeBool(rsRaw);
    }
    if (rsKey == u"Favorite")
    {
        return normalizeBool(rsRaw);
    }
    if (rsKey == u"Order")
    {
        // Clamp to a non-negative index; a malformed value fails closed.
        sal_Int64 nVal = 0;
        if (parseInt(rsRaw, nVal))
        {
            if (nVal < 0)
                nVal = 0;
            return { true, OUString::number(nVal) };
        }
        return { false, OUString() };
    }
    if (rsKey == u"GroupId")
    {
        return IsValidGroupId(rsRaw) ? Result{ true, rsRaw }
                                     : Result{ false, OUString() };
    }
    if (rsKey == u"FontSize")
    {
        // Clamp to [MIN_FONT_SIZE, MAX_FONT_SIZE]; malformed -> default.
        sal_Int64 nVal = 0;
        if (!parseInt(rsRaw, nVal))
            return { false, OUString() };
        if (nVal < MIN_FONT_SIZE)
            nVal = MIN_FONT_SIZE;
        else if (nVal > MAX_FONT_SIZE)
            nVal = MAX_FONT_SIZE;
        return { true, OUString::number(nVal) };
    }
    if (rsKey == u"TextColor")
    {
        return IsValidHexColor(rsRaw) ? Result{ true, rsRaw }
                                      : Result{ false, OUString() };
    }
    if (rsKey == u"BackgroundColor")
    {
        return IsValidHexColor(rsRaw) ? Result{ true, rsRaw }
                                      : Result{ false, OUString() };
    }
    if (rsKey == u"FontFamily")
    {
        return IsValidFontFamily(rsRaw) ? Result{ true, rsRaw }
                                        : Result{ false, OUString() };
    }
    if (rsKey == u"Bold")
    {
        return normalizeBool(rsRaw);
    }
    if (rsKey == u"Italic")
    {
        return normalizeBool(rsRaw);
    }
    if (rsKey == u"Underline")
    {
        return normalizeBool(rsRaw);
    }

    // Unknown key: fail closed. Forward-compat preservation of unknown keys is
    // the caller's concern (it keeps the raw entry); this normalizer never
    // vouches for a value it does not recognise.
    return { false, OUString() };
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
