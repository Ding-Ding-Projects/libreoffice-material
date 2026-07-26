/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#ifndef INCLUDED_SFX2_SOURCE_INC_SFXDOCUMENTTABBAR_HXX
#define INCLUDED_SFX2_SOURCE_INC_SFXDOCUMENTTABBAR_HXX

#include <sal/config.h>

#include <svtools/tabbar.hxx>
#include <tools/color.hxx>
#include <rtl/ustring.hxx>

#include <map>
#include <vector>

/**
 * Material document-tab STRIP (stage 3 of the tabbed-UI feature).
 *
 * SfxDocumentTabBar is a svtools::TabBar subclass that renders one tab per open
 * document and, on tab activation, RAISES that document's already-existing
 * top-level window. It drives the existing one-window-per-document model; it
 * does NOT host multiple documents inside one window (that stays deferred).
 *
 * It rides the already-shipped Material TabBar paint path exactly as
 * ScTabControl (the Calc sheet-tab strip) does -- see
 * qa/windows-ui-contract/calc-sheet-tabs.json. The base svtools::TabBar owns
 * layout, scrolling and the tab fills; this subclass adds, purely on top and
 * only while the Material file-widget theme is active, the @outline-variant
 * strip top rule and the per-tab @stroke-standard colour accent strip held out
 * of the base full-tab fill (docs/design/05-navigation.md 6). Every rendered
 * attribute (label, colour, pin, order) comes from each document's persisted
 * SfxDocTabStyle (stage 2); nothing is hardcoded.
 *
 * FAIL-CLOSED GUARD. The strip is opt-in and inert by default. Create() returns
 * nullptr -- so the widget cannot even be constructed -- unless BOTH
 *   officecfg::Office::Common::DocumentTabs::TabsEnabled == true, AND
 *   the Material file-widget theme is active (VCL_FILE_WIDGET_THEME=material,
 *   high contrast not resolved).
 * When tabs are off the caller holds a null pointer and shows nothing, so the
 * default build path is byte-identical for users who do not enable tabs.
 *
 * NOTE: compile-plausibility only in this stage. It follows sfx2 conventions and
 * is registered in sfx2/Library_sfx.mk, but is compiled by CI, not locally, and
 * no runtime rendering or window-switching is claimed. The build-free contract
 * qa/windows-ui-contract/document-tab-strip.json pins the source shape.
 */

namespace com::sun::star::frame { class XFrame; }

class SfxDocumentTabBar final : public TabBar
{
    // VclPtr<T>::Create() is the only sanctioned way to build a VCL window, and
    // it needs access to the private constructor below. Declaring it a friend
    // keeps the constructor private so Create() (with its TabsEnabled guard)
    // stays the single entry point.
    friend class VclPtr<SfxDocumentTabBar>;

public:
    /**
     * Guarded factory: the ONLY way to obtain a strip. Returns nullptr -- so no
     * widget is constructed and nothing is shown -- unless the TabsEnabled
     * officecfg guard is true AND the Material theme is active. This is the seam
     * that keeps the tabs-off build byte-identical.
     */
    static VclPtr<SfxDocumentTabBar> Create(vcl::Window* pParent);

    /** True only when TabsEnabled is set in officecfg (stage-2 group, default
     *  false). Static so callers can gate window/chrome layout without a widget. */
    static bool IsTabsEnabled();

    virtual ~SfxDocumentTabBar() override;
    virtual void dispose() override;

    /** Rebuild the tabs from the currently open document frames, reading each
     *  document's persisted SfxDocTabStyle for label/colour/pin/order. */
    void Rebuild();

private:
    explicit SfxDocumentTabBar(vcl::Window* pParent);

    /// One row per rendered tab: the tab page id and the frame it raises.
    struct TabEntry
    {
        sal_uInt16 nPageId;
        css::uno::Reference<css::frame::XFrame> xFrame;
    };
    std::vector<TabEntry> maEntries;

    /// User tab colours held out of the base full-tab fill while the Material
    /// theme is active, drawn as an accent strip under the label instead
    /// (mirrors ScTabControl::maMaterialTabColors; design 6.4).
    std::map<sal_uInt16, Color> maMaterialTabColors;

    /// True only when VCL_FILE_WIDGET_THEME=material is the active theme and
    /// high contrast is not resolved (the native baseline bypass). Identical
    /// posture to ScTabControl::IsMaterialSheetTabActive().
    bool IsMaterialDocTabActive() const;

    /// Route a document tab colour: under the Material theme record it for the
    /// accent-strip overlay and leave the base tab neutral; otherwise fall back
    /// to the base full-fill so the colour can never vanish.
    void SetMaterialAwareTabBgColor(sal_uInt16 nPageId, const Color& rColor);

    /// Draw the Material strip top rule and per-tab colour accent strips on top
    /// of the base paint; never consults the selection state.
    void PaintMaterialDocTabOverlay(vcl::RenderContext& rRenderContext);

    /// Raise the document window bound to a tab, via the EXACT existing
    /// frame-activation path the Window menu uses.
    void RaiseFrameForPage(sal_uInt16 nPageId);

    /// Look up the frame bound to a page id, or an empty reference.
    css::uno::Reference<css::frame::XFrame> FrameForPage(sal_uInt16 nPageId) const;

    /// Open the per-tab appearance editor for a page (right-click context menu).
    void EditTabAppearance(sal_uInt16 nPageId);

protected:
    virtual void Paint(vcl::RenderContext& rRenderContext,
                       const tools::Rectangle& rRect) override;
    virtual void Select() override;
    virtual void Command(const CommandEvent& rCEvt) override;
};

#endif // INCLUDED_SFX2_SOURCE_INC_SFXDOCUMENTTABBAR_HXX

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
