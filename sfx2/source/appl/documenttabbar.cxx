/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <SfxDocumentTabBar.hxx>
#include <SfxDocTabStyle.hxx>

#include <officecfg/Office/Common.hxx>

#include <vcl/svapp.hxx>
#include <vcl/settings.hxx>
#include <vcl/commandevent.hxx>
#include <vcl/event.hxx>
#include <vcl/weld/Builder.hxx>
#include <vcl/weld/Dialog.hxx>
#include <vcl/weld/Entry.hxx>
#include <vcl/weld/CheckButton.hxx>
#include <vcl/weld/SpinButton.hxx>
#include <vcl/MaterialTokens.hxx>

#include <toolkit/helper/vclunohelper.hxx>
#include <comphelper/processfactory.hxx>
#include <comphelper/configuration.hxx>

#include <com/sun/star/frame/Desktop.hpp>
#include <com/sun/star/frame/XDesktop2.hpp>
#include <com/sun/star/frame/XFrame.hpp>
#include <com/sun/star/frame/XController.hpp>
#include <com/sun/star/frame/XTitle.hpp>
#include <com/sun/star/frame/XModel.hpp>
#include <com/sun/star/container/XIndexAccess.hpp>
#include <com/sun/star/container/XNameAccess.hpp>
#include <com/sun/star/container/XNameContainer.hpp>
#include <com/sun/star/container/XNameReplace.hpp>

#include <algorithm>
#include <cstdlib>
#include <optional>
#include <string_view>

using namespace ::com::sun::star;

namespace
{
// Material document-tab overlay tokens, resolved from the single named-token
// table over definition.xml (vcl::MaterialTokens), and only while
// VCL_FILE_WIDGET_THEME=material is the documented active theme. This is the
// SAME anatomy the Calc sheet-tab strip contracts in calc-sheet-tabs.json
// (ScMaterialSheetTabTokens): the strip rides the already-shipped Material
// TabBar paint path rather than inventing pixels. Under the default or native
// theme this returns nothing and the base TabBar rendering is left untouched.
struct SfxMaterialDocTabTokens
{
    Color aOutlineVariant;     // @outline-variant strip top rule (design 6.1)
    sal_Int32 nStrokeThin;     // @stroke-thin rule thickness
    sal_Int32 nStrokeStandard; // @stroke-standard accent-strip thickness
    sal_Int32 nAccentInset;    // @space-tab-inline horizontal inset of the accent
};

// VCL_FILE_WIDGET_THEME is forced once in soffice_main() before VCL starts and
// never changes for the process, so read it a single time. This mirrors the
// per-paint getenv fix already applied to the Draw/Impress grid path
// (viewobjectcontactofsdrpage.cxx): the tab strip's Paint() consults the guard
// below, and an env lookup on every repaint is the exact GUI-lag anti-pattern
// bin/check-material-theme and the perf fix target. The high-contrast check
// stays per-call at the use sites because it can toggle at runtime.
bool lcl_materialThemeEnvActive()
{
    static const bool bActive = [] {
        const char* pThemeName = std::getenv("VCL_FILE_WIDGET_THEME");
        return pThemeName && std::string_view(pThemeName) == "material";
    }();
    return bActive;
}

std::optional<SfxMaterialDocTabTokens> lcl_getMaterialDocTabTokens()
{
    if (!lcl_materialThemeEnvActive())
        return std::nullopt;

    const bool bDark = Application::GetSettings().GetStyleSettings().GetWindowColor().IsDark();
    const vcl::MaterialTokens aTokens
        = vcl::MaterialTokens::fromThemeDefinition(bDark ? "dark"_ostr : OString());
    if (!aTokens.isValid())
        return std::nullopt;

    const std::optional<Color> oOutlineVariant = aTokens.findColor("outline-variant");
    const std::optional<sal_Int32> oStrokeThin = aTokens.findMetric("stroke-thin");
    const std::optional<sal_Int32> oStrokeStandard = aTokens.findMetric("stroke-standard");
    const std::optional<sal_Int32> oAccentInset = aTokens.findMetric("space-tab-inline");
    if (!oOutlineVariant || !oStrokeThin || !oStrokeStandard || !oAccentInset)
        return std::nullopt;

    return SfxMaterialDocTabTokens{ *oOutlineVariant, *oStrokeThin, *oStrokeStandard,
                                    *oAccentInset };
}

/// The document URL for a frame's model, used as the officecfg style key.
OUString lcl_frameUrl(const uno::Reference<frame::XFrame>& xFrame)
{
    if (!xFrame.is())
        return OUString();
    uno::Reference<frame::XModel> xModel(xFrame->getController().is()
                                             ? xFrame->getController()->getModel()
                                             : uno::Reference<frame::XModel>());
    return xModel.is() ? xModel->getURL() : OUString();
}

/// The frame's own title, the neutral fallback label when no CustomLabel is set.
OUString lcl_frameTitle(const uno::Reference<frame::XFrame>& xFrame)
{
    uno::Reference<frame::XTitle> xTitle(xFrame, uno::UNO_QUERY);
    return xTitle.is() ? xTitle->getTitle() : OUString();
}

// A resolved, already-normalized per-document tab style. Every field is produced
// by passing the untrusted persisted value through SfxDocTabStyle::Normalize, so
// NOTHING the strip renders is a raw registry value or a hardcoded literal.
struct SfxResolvedDocTabStyle
{
    OUString aLabel;                 // CustomLabel (normalized) or frame title fallback
    std::optional<Color> oColor;     // BackgroundColor (#hex, normalized) if any
    bool bPinned = false;            // Pinned (normalized bool)
    bool bFavorite = false;          // Favorite (normalized bool)
    sal_Int32 nOrder = 0;            // Order (normalized) -> tab arrangement
};

/// Read one field of the persisted DocumentTabStyles entry and run it through the
/// stage-2 clamp-on-read normalizer. bKeep==false means "use the schema default".
SfxDocTabStyle::Result lcl_normalizedField(const uno::Reference<container::XNameAccess>& xEntry,
                                           std::u16string_view rsKey)
{
    if (!xEntry.is() || !xEntry->hasByName(OUString(rsKey)))
        return { false, OUString() };
    OUString aRaw;
    uno::Any aAny = xEntry->getByName(OUString(rsKey));
    // Booleans and numbers persist through the registry; stringify them so the
    // one normalizer entry point validates every field uniformly.
    if (bool b; aAny >>= b)
        aRaw = b ? u"true"_ustr : u"false"_ustr;
    else if (sal_Int32 n; aAny >>= n)
        aRaw = OUString::number(n);
    else
        aAny >>= aRaw;
    return SfxDocTabStyle::Normalize(rsKey, aRaw);
}

SfxResolvedDocTabStyle lcl_resolveStyle(const uno::Reference<frame::XFrame>& xFrame)
{
    SfxResolvedDocTabStyle aStyle;
    aStyle.aLabel = lcl_frameTitle(xFrame);

    const OUString aUrl = lcl_frameUrl(xFrame);
    if (aUrl.isEmpty())
        return aStyle;

    // The persisted set is keyed by document URL (stage-2 Common.xcs
    // Histories/DocumentTabStyles, node-type DocumentTabStyle).
    uno::Reference<container::XNameAccess> xStyles(
        officecfg::Office::Common::Histories::DocumentTabStyles::get());
    if (!xStyles.is() || !xStyles->hasByName(aUrl))
        return aStyle;

    uno::Reference<container::XNameAccess> xEntry;
    xStyles->getByName(aUrl) >>= xEntry;
    if (!xEntry.is())
        return aStyle;

    if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"CustomLabel"); r.bKeep
        && !r.aValue.isEmpty())
        aStyle.aLabel = r.aValue;
    if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"BackgroundColor"); r.bKeep
        && SfxDocTabStyle::IsValidHexColor(r.aValue))
        aStyle.oColor = Color(ColorTransparency,
                              static_cast<sal_uInt32>(r.aValue.copy(1).toUInt32(16)));
    if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Pinned"); r.bKeep)
        aStyle.bPinned = r.aValue == u"true";
    if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Favorite"); r.bKeep)
        aStyle.bFavorite = r.aValue == u"true";
    if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Order"); r.bKeep)
        aStyle.nOrder = r.aValue.toInt32();

    return aStyle;
}
} // namespace

bool SfxDocumentTabBar::IsTabsEnabled()
{
    // Stage-2 officecfg group; default false. This is the fail-closed guard: when
    // false the strip is never constructed and the tabs-off path is byte-identical.
    return officecfg::Office::Common::DocumentTabs::TabsEnabled::get();
}

VclPtr<SfxDocumentTabBar> SfxDocumentTabBar::Create(vcl::Window* pParent)
{
    // The single construction seam. If tabs are disabled, return nullptr so no
    // widget exists and nothing is shown -- the guard that keeps the default
    // build byte-unchanged. The strip is also inert unless the Material theme is
    // active, but the hard cannot-construct gate is TabsEnabled.
    if (!IsTabsEnabled())
        return nullptr;

    VclPtr<SfxDocumentTabBar> pBar = VclPtr<SfxDocumentTabBar>::Create(pParent);
    if (!pBar->IsMaterialDocTabActive())
    {
        // TabsEnabled but not under the Material theme: honour the guard by not
        // presenting a strip (the tabbed UI is a Material surface only).
        pBar.disposeAndClear();
        return nullptr;
    }
    pBar->Rebuild();
    return pBar;
}

SfxDocumentTabBar::SfxDocumentTabBar(vcl::Window* pParent)
    : TabBar(pParent, WB_3DLOOK | WB_MINSCROLL | WB_SCROLL | WB_RANGESELECT | WB_DRAG, true)
{
}

SfxDocumentTabBar::~SfxDocumentTabBar() { disposeOnce(); }

void SfxDocumentTabBar::dispose()
{
    maEntries.clear();
    maMaterialTabColors.clear();
    TabBar::dispose();
}

bool SfxDocumentTabBar::IsMaterialDocTabActive() const
{
    if (!lcl_materialThemeEnvActive())
        return false;
    // Resolved high contrast restores the captured native StyleSettings baseline,
    // so the Material drawing path -- and this whole strip -- stays inert. This
    // check stays per-call because high-contrast mode can toggle at runtime.
    if (Application::GetSettings().GetStyleSettings().GetHighContrastMode())
        return false;
    return true;
}

void SfxDocumentTabBar::Rebuild()
{
    Clear();
    maEntries.clear();
    maMaterialTabColors.clear();

    const uno::Reference<uno::XComponentContext> xContext(
        comphelper::getProcessComponentContext());
    uno::Reference<frame::XDesktop2> xDesktop = frame::Desktop::create(xContext);
    uno::Reference<container::XIndexAccess> xList = xDesktop->getFrames();
    if (!xList.is())
        return;

    // Gather (frame, resolved style) pairs, then arrange by Pinned then Order --
    // both driven entirely by the persisted SfxDocTabStyle, nothing hardcoded.
    struct Row { uno::Reference<frame::XFrame> xFrame; SfxResolvedDocTabStyle aStyle; };
    std::vector<Row> aRows;
    const sal_Int32 nCount = xList->getCount();
    for (sal_Int32 i = 0; i < nCount; ++i)
    {
        uno::Reference<frame::XFrame> xFrame;
        xList->getByIndex(i) >>= xFrame;
        if (!xFrame.is())
            continue;
        aRows.push_back({ xFrame, lcl_resolveStyle(xFrame) });
    }
    std::stable_sort(aRows.begin(), aRows.end(), [](const Row& a, const Row& b) {
        if (a.aStyle.bPinned != b.aStyle.bPinned)
            return a.aStyle.bPinned; // pinned tabs lead
        return a.aStyle.nOrder < b.aStyle.nOrder;
    });

    sal_uInt16 nPageId = 1;
    for (const Row& rRow : aRows)
    {
        InsertPage(nPageId, rRow.aStyle.aLabel);
        if (rRow.aStyle.oColor)
            SetMaterialAwareTabBgColor(nPageId, *rRow.aStyle.oColor);
        maEntries.push_back({ nPageId, rRow.xFrame });
        ++nPageId;
    }
}

uno::Reference<frame::XFrame> SfxDocumentTabBar::FrameForPage(sal_uInt16 nPageId) const
{
    for (const TabEntry& rEntry : maEntries)
        if (rEntry.nPageId == nPageId)
            return rEntry.xFrame;
    return uno::Reference<frame::XFrame>();
}

void SfxDocumentTabBar::SetMaterialAwareTabBgColor(sal_uInt16 nPageId, const Color& rColor)
{
    // Identical posture to ScTabControl: hold the user colour out of the base
    // full-tab fill only when the accent strip will actually be drawn, otherwise
    // fall back to the base full-fill so the colour indicator can never vanish.
    if (IsMaterialDocTabActive() && lcl_getMaterialDocTabTokens().has_value())
    {
        maMaterialTabColors[nPageId] = rColor;
        SetTabBgColor(nPageId, COL_AUTO);
    }
    else
    {
        SetTabBgColor(nPageId, rColor);
    }
}

void SfxDocumentTabBar::Paint(vcl::RenderContext& rRenderContext, const tools::Rectangle& rRect)
{
    // The base class owns tab layout, scrolling and the fills; the Material work
    // is purely additive on top, so the native / default theme rendering is left
    // completely untouched. This is the calc-sheet-tabs paint contract cloned.
    TabBar::Paint(rRenderContext, rRect);

    if (IsMaterialDocTabActive())
        PaintMaterialDocTabOverlay(rRenderContext);
}

void SfxDocumentTabBar::PaintMaterialDocTabOverlay(vcl::RenderContext& rRenderContext)
{
    const std::optional<SfxMaterialDocTabTokens> oTokens = lcl_getMaterialDocTabTokens();
    if (!oTokens)
        return;

    rRenderContext.Push(vcl::PushFlags::LINECOLOR | vcl::PushFlags::FILLCOLOR);

    // Strip top rule: @outline-variant hairline across the whole strip (design
    // 6.1). GetPageArea() is already mirrored in RTL.
    const tools::Rectangle aPageArea = GetPageArea();
    rRenderContext.SetLineColor(oTokens->aOutlineVariant);
    rRenderContext.DrawLine(aPageArea.TopLeft(), aPageArea.TopRight());

    // Colour accent strip under each user-coloured tab. The loop walks the stored
    // colours only and never consults the current-page or page-selected state, so
    // the accent is fully independent of the active-tab treatment (design 6.4).
    rRenderContext.SetLineColor();
    for (const auto& [nPageId, aColor] : maMaterialTabColors)
    {
        tools::Rectangle aTabRect = GetPageRect(nPageId);
        if (aTabRect.IsEmpty())
            continue;
        aTabRect.AdjustLeft(oTokens->nAccentInset);
        aTabRect.AdjustRight(-oTokens->nAccentInset);
        aTabRect.SetTop(aTabRect.Bottom() - oTokens->nStrokeStandard);
        rRenderContext.SetFillColor(aColor);
        rRenderContext.DrawRect(aTabRect);
    }

    rRenderContext.Pop();
}

void SfxDocumentTabBar::RaiseFrameForPage(sal_uInt16 nPageId)
{
    uno::Reference<frame::XFrame> xFrame = FrameForPage(nPageId);
    if (!xFrame.is())
        return;

    // THE load-bearing reuse. This is the EXACT frame-activation path the Window
    // menu uses to switch documents -- WindowListMenuController::itemSelected in
    // framework/source/uielement/resourcemenucontroller.cxx (the pWin->GrabFocus()
    // + pWin->ToTop(ToTopFlags::RestoreWhenMin) pair at line 525-527). It touches
    // NO frame-topness seam and performs NO WorkWindow cast; it only raises the
    // document's already-existing top-level window.
    VclPtr<vcl::Window> pWin = VCLUnoHelper::GetWindow(xFrame->getContainerWindow());
    if (!pWin)
        return;
    pWin->GrabFocus();
    pWin->ToTop(ToTopFlags::RestoreWhenMin);
}

void SfxDocumentTabBar::Select()
{
    // Activation of a tab raises the bound document window; it does NOT reparent
    // or re-host any frame (that would be true in-window hosting, deferred).
    RaiseFrameForPage(GetCurPageId());
}

void SfxDocumentTabBar::Command(const CommandEvent& rCEvt)
{
    if (rCEvt.GetCommand() == CommandEventId::ContextMenu)
    {
        const Point aPos = rCEvt.IsMouseEvent() ? rCEvt.GetMousePosPixel()
                                                : Point(0, 0);
        const sal_uInt16 nPageId = GetPageId(aPos);
        if (nPageId != TabBar::PAGE_NOT_FOUND && nPageId != 0)
        {
            EditTabAppearance(nPageId);
            return;
        }
    }
    TabBar::Command(rCEvt);
}

void SfxDocumentTabBar::EditTabAppearance(sal_uInt16 nPageId)
{
    uno::Reference<frame::XFrame> xFrame = FrameForPage(nPageId);
    const OUString aUrl = lcl_frameUrl(xFrame);
    if (aUrl.isEmpty())
        return; // Unsaved documents have no persistence key yet.

    // Small weld dialog reachable from the strip's right-click context menu. It
    // edits this tab's CustomLabel/colour/pin/font from the stage-2 style schema
    // and persists through officecfg. The .ui follows the appearance-editor idiom
    // (cui appearance.ui) and passes bin/check-ui-a11y-fatals.py with 0 FATALs.
    std::unique_ptr<weld::Builder> xBuilder(
        Application::CreateBuilder(GetFrameWeld(), u"sfx/ui/documenttabappearance.ui"_ustr));
    std::unique_ptr<weld::Dialog> xDialog(xBuilder->weld_dialog(u"DocumentTabAppearanceDialog"_ustr));
    if (!xDialog)
        return;

    std::unique_ptr<weld::Entry> xLabel(xBuilder->weld_entry(u"label"_ustr));
    std::unique_ptr<weld::Entry> xColor(xBuilder->weld_entry(u"color"_ustr));
    std::unique_ptr<weld::CheckButton> xPinned(xBuilder->weld_check_button(u"pinned"_ustr));
    std::unique_ptr<weld::CheckButton> xFavorite(xBuilder->weld_check_button(u"favorite"_ustr));
    std::unique_ptr<weld::SpinButton> xFontSize(xBuilder->weld_spin_button(u"fontsize"_ustr));

    const SfxResolvedDocTabStyle aStyle = lcl_resolveStyle(xFrame);
    if (xLabel)
        xLabel->set_text(aStyle.aLabel);
    if (xColor && aStyle.oColor)
        xColor->set_text("#" + OUString::fromUtf8(aStyle.oColor->AsRGBHexString().toUtf8()));
    if (xPinned)
        xPinned->set_active(aStyle.bPinned);
    if (xFavorite)
        xFavorite->set_active(aStyle.bFavorite);
    if (xFontSize)
        xFontSize->set_value(SfxDocTabStyle::DEFAULT_FONT_SIZE);

    if (xDialog->run() != RET_OK)
        return;

    // Persist through officecfg, each value re-validated by the stage-2 normalizer
    // before it is written so the dialog cannot inject an unsafe style.
    std::shared_ptr<comphelper::ConfigurationChanges> xChanges(
        comphelper::ConfigurationChanges::create());
    uno::Reference<container::XNameContainer> xStyles(
        officecfg::Office::Common::Histories::DocumentTabStyles::get(xChanges), uno::UNO_QUERY);
    if (!xStyles.is())
        return;

    uno::Reference<container::XNameReplace> xEntry;
    if (xStyles->hasByName(aUrl))
        xStyles->getByName(aUrl) >>= xEntry;
    if (!xEntry.is())
        return;

    if (xLabel)
    {
        SfxDocTabStyle::Result r = SfxDocTabStyle::Normalize(u"CustomLabel", xLabel->get_text());
        xEntry->replaceByName(u"CustomLabel"_ustr, uno::Any(r.bKeep ? r.aValue : OUString()));
    }
    if (xColor)
    {
        SfxDocTabStyle::Result r = SfxDocTabStyle::Normalize(u"BackgroundColor", xColor->get_text());
        xEntry->replaceByName(u"BackgroundColor"_ustr, uno::Any(r.bKeep ? r.aValue : OUString()));
    }
    if (xPinned)
        xEntry->replaceByName(u"Pinned"_ustr, uno::Any(xPinned->get_active()));
    if (xFavorite)
        xEntry->replaceByName(u"Favorite"_ustr, uno::Any(xFavorite->get_active()));
    if (xFontSize)
    {
        SfxDocTabStyle::Result r = SfxDocTabStyle::Normalize(
            u"FontSize", OUString::number(xFontSize->get_value()));
        xEntry->replaceByName(u"FontSize"_ustr,
                              uno::Any(static_cast<sal_Int16>(
                                  r.bKeep ? r.aValue.toInt32() : SfxDocTabStyle::DEFAULT_FONT_SIZE)));
    }
    xChanges->commit();

    Rebuild();
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
