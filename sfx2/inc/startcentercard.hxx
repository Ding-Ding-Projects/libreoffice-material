/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#pragma once

#include <rtl/ustring.hxx>
#include <tools/long.hxx>

#include <vector>

// vcl::RenderContext is a typedef for OutputDevice; forward-declare the class.
class OutputDevice;
namespace vcl { typedef OutputDevice RenderContext; }
class ThumbnailView;
class ThumbnailViewItem;

namespace sfx2
{
/**
 * Native Material Start Center document-card anatomy.
 *
 * The Start Center's Recent Documents and Templates grids are card grids, per
 * docs/design/06-containers.md 6.6 and docs/design/09-start-center.md 9.1/9.10.
 * These metrics are the normative card geometry taken from those chapters (which
 * win over the prototype where they differ) and mirrored 1:1 by the fail-closed
 * contract bin/check-windows-startcenter-cards.py. The color/radius *values* are
 * never hard-coded here: they are resolved at draw time from the single Material
 * token table (vcl::MaterialTokens over definition.xml).
 *
 * Everything below is opt-in: it is drawn only when the documented Material
 * file-widget activation (VCL_FILE_WIDGET_THEME=material) is live. Under the
 * default/native theme IsMaterialStartCenterActive() is false and every entry
 * point is inert, so the existing ThumbnailView drawing path is untouched.
 */

// --- Card anatomy geometry (device pixels) -----------------------------------
inline constexpr tools::Long SC_CARD_MIN_WIDTH = 184;      ///< grid minmax() minimum card width
inline constexpr tools::Long SC_CARD_GRID_GAP = 16;        ///< grid gap between cards
inline constexpr tools::Long SC_CARD_PREVIEW_HEIGHT = 118; ///< preview region height
inline constexpr tools::Long SC_CARD_CAPTION_HEIGHT = 52;  ///< caption region height (10/12/12 pad + name + meta)
inline constexpr tools::Long SC_CARD_THUMB_WIDTH = 74;     ///< page-thumbnail placeholder width
inline constexpr tools::Long SC_CARD_THUMB_HEIGHT = 92;    ///< page-thumbnail placeholder height
inline constexpr tools::Long SC_CARD_THUMB_RADIUS = 6;     ///< page-thumbnail corner radius
inline constexpr tools::Long SC_CARD_BADGE_SIZE = 26;      ///< app-badge chip size
inline constexpr tools::Long SC_CARD_BADGE_INSET = 8;      ///< app-badge inset from preview top-right
inline constexpr tools::Long SC_CARD_BADGE_ICON = 16;      ///< app-badge glyph size
inline constexpr tools::Long SC_CARD_CAPTION_PAD_X = 12;   ///< caption horizontal padding
inline constexpr tools::Long SC_CARD_CAPTION_PAD_TOP = 10; ///< caption top padding
inline constexpr tools::Long SC_CARD_CAPTION_PAD_BOTTOM = 12; ///< caption bottom padding
inline constexpr tools::Long SC_CARD_TITLE_TEXT = 13;      ///< card title size (medium)
inline constexpr tools::Long SC_CARD_META_TEXT = 11;       ///< card meta size
inline constexpr tools::Long SC_CARD_META_GAP = 2;         ///< gap between title and meta
inline constexpr tools::Long SC_CARD_EMPTY_PADDING = 34;   ///< empty/filtered-grid message padding
inline constexpr tools::Long SC_CARD_EMPTY_TEXT = 13;      ///< empty/filtered-grid message size
inline constexpr tools::Long SC_CARD_INVITE_TITLE_TEXT = 18; ///< first-run invitation title size
inline constexpr tools::Long SC_CARD_INVITE_BODY_TEXT = 13;  ///< first-run invitation body size
inline constexpr tools::Long SC_CARD_INVITE_GAP = 8;         ///< gap between invitation title and body

/**
 * What the card renderer draws when no card is visible.
 *
 * The Start Center recent/template grids distinguish two empty conditions,
 * following docs/design/09-start-center.md 9.5:
 *   - a genuinely empty grid (first run / nothing to show, @c bFiltered false):
 *     the recent grid draws the first-run "create or open a document" invitation
 *     (@c aInviteTitle + @c aInviteBody); a view with no invitation (the template
 *     grid) leaves the @surface background blank rather than a filter-implying line;
 *   - a filtered-empty grid (a live search hid every card, @c bFiltered true):
 *     the centred @c aFilteredMessage "no match" cell.
 * The invitation deliberately replaces the legacy Welcome bitmap on the Material
 * path; that bitmap survives only on the stock (non-Material) fallback.
 */
struct MaterialStartCenterEmptyState
{
    OUString aInviteTitle;    ///< first-run invitation title (empty => view has no invitation)
    OUString aInviteBody;     ///< first-run invitation body
    OUString aFilteredMessage; ///< filtered-empty "no match" message
    bool bFiltered = false;   ///< true: backing list has items but all are filtered out
};

/// True only when the documented Material file-widget theme is the active
/// activation (VCL_FILE_WIDGET_THEME=material). Mirrors the guard in
/// sd/source/ui/app/scalectrl.cxx so non-Material rendering paths stay inert.
bool IsMaterialStartCenterActive();

class MaterialStartCenterCards
{
public:
    /**
     * Paint the full Material card grid for @p rItems into @p rRenderContext.
     *
     * When @p rItems is empty the renderer draws the empty state described by
     * @p rEmptyState (first-run invitation or filtered "no match" cell) instead
     * of a card grid.
     *
     * @return true when the Material theme is active and the grid (or the empty
     *         state) was drawn; false when the Material theme is inactive or the
     *         token table is unreadable, in which case nothing is drawn and the
     *         caller must fall back to the default ThumbnailView paint.
     */
    static bool Paint(vcl::RenderContext& rRenderContext, ThumbnailView& rView,
                      const std::vector<ThumbnailViewItem*>& rItems,
                      const MaterialStartCenterEmptyState& rEmptyState);
};

} // namespace sfx2

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
