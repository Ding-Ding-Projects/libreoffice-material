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
#include <sfx2/frame.hxx>

#include <officecfg/Office/Common.hxx>

#include <tools/mapunit.hxx>

#include <vcl/svapp.hxx>
#include <vcl/settings.hxx>
#include <vcl/commandevent.hxx>
#include <vcl/event.hxx>
#include <vcl/font.hxx>
#include <vcl/mapmod.hxx>
#include <vcl/outdev.hxx>
#include <vcl/weld/Builder.hxx>
#include <vcl/weld/Dialog.hxx>
#include <vcl/weld/Entry.hxx>
#include <vcl/weld/CheckButton.hxx>
#include <vcl/weld/SpinButton.hxx>
#include <vcl/MaterialTokens.hxx>

#include <toolkit/helper/vclunohelper.hxx>
#include <comphelper/processfactory.hxx>
#include <comphelper/configuration.hxx>
#include <comphelper/propertysequence.hxx>

#include <com/sun/star/frame/XFrame.hpp>
#include <com/sun/star/frame/XController.hpp>
#include <com/sun/star/frame/XTitle.hpp>
#include <com/sun/star/frame/XModel.hpp>
#include <com/sun/star/container/XNameAccess.hpp>
#include <com/sun/star/container/XNameContainer.hpp>
#include <com/sun/star/beans/XPropertySet.hpp>
#include <com/sun/star/configuration/theDefaultProvider.hpp>
#include <com/sun/star/lang/XMultiServiceFactory.hpp>
#include <com/sun/star/lang/XSingleServiceFactory.hpp>
#include <com/sun/star/util/XChangesBatch.hpp>

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
        = vcl::MaterialTokens::fromCurrentTheme(bDark);
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

sal_Int16 lcl_tabWidthSetting()
{
    try
    {
        return officecfg::Office::Common::DocumentTabs::TabWidth::get();
    }
    catch (const uno::Exception&)
    {
        return 1;
    }
}

sal_Int16 lcl_tabDensitySetting()
{
    try
    {
        return officecfg::Office::Common::DocumentTabs::TabDensity::get();
    }
    catch (const uno::Exception&)
    {
        return 0;
    }
}

/// Open the per-document tab-style SET from the configuration.
///
/// A dynamic set (Common.xcs History/DocumentTabStyles) gets no generated
/// officecfg accessor -- only scalar groups do -- so it must be opened through
/// the configuration provider. This is the same ConfigurationAccess /
/// ConfigurationUpdateAccess pattern sfx2 already uses in
/// sfx2/source/doc/doctemplates.cxx. Returns an empty reference on any failure
/// so every caller degrades to schema defaults rather than throwing.
uno::Reference<uno::XInterface> lcl_openTabStyleSet(bool bWritable)
{
    try
    {
        const uno::Reference<uno::XComponentContext>& xContext
            = comphelper::getProcessComponentContext();
        uno::Reference<lang::XMultiServiceFactory> xConfigProvider(
            configuration::theDefaultProvider::get(xContext));
        uno::Sequence<uno::Any> aArgs(comphelper::InitAnyPropertySequence(
            { { "nodepath",
                uno::Any(u"/org.openoffice.Office.Common/History/DocumentTabStyles"_ustr) } }));
        return xConfigProvider->createInstanceWithArguments(
            bWritable ? u"com.sun.star.configuration.ConfigurationUpdateAccess"_ustr
                      : u"com.sun.star.configuration.ConfigurationAccess"_ustr,
            aArgs);
    }
    catch (const uno::Exception&)
    {
        return uno::Reference<uno::XInterface>();
    }
}

/// The document URL for a frame's model, used as the officecfg style key.
OUString lcl_frameUrl(const uno::Reference<frame::XFrame>& xFrame)
{
    if (!xFrame.is())
        return OUString();
    try
    {
        const uno::Reference<frame::XController> xController = xFrame->getController();
        const uno::Reference<frame::XModel> xModel(
            xController.is() ? xController->getModel() : uno::Reference<frame::XModel>());
        return xModel.is() ? xModel->getURL() : OUString();
    }
    catch (const uno::Exception&)
    {
        return OUString();
    }
}

/// The frame's own title, the neutral fallback label when no CustomLabel is set.
OUString lcl_frameTitle(const uno::Reference<frame::XFrame>& xFrame)
{
    try
    {
        uno::Reference<frame::XTitle> xTitle(xFrame, uno::UNO_QUERY);
        return xTitle.is() ? xTitle->getTitle() : OUString();
    }
    catch (const uno::Exception&)
    {
        return OUString();
    }
}

/// True only for a live top-level frame with an attached document model.
bool lcl_isLiveDocumentFrame(const uno::Reference<frame::XFrame>& xFrame)
{
    if (!xFrame.is())
        return false;
    try
    {
        if (!xFrame->getContainerWindow().is())
            return false;
        const uno::Reference<frame::XController> xController = xFrame->getController();
        return xController.is() && xController->getModel().is();
    }
    catch (const uno::Exception&)
    {
        return false;
    }
}

sal_uInt8 lcl_hexDigit(sal_Unicode c)
{
    if (c >= '0' && c <= '9')
        return static_cast<sal_uInt8>(c - '0');
    if (c >= 'a' && c <= 'f')
        return static_cast<sal_uInt8>(c - 'a' + 10);
    return static_cast<sal_uInt8>(c - 'A' + 10);
}

sal_uInt8 lcl_hexByte(const OUString& rColor, sal_Int32 nOffset)
{
    return static_cast<sal_uInt8>((lcl_hexDigit(rColor[nOffset]) << 4)
                                  | lcl_hexDigit(rColor[nOffset + 1]));
}

/// Decode CSS-style #rgb, #rrggbb, and #rrggbbaa without losing alpha.
std::optional<Color> lcl_parseHexColor(const OUString& rColor)
{
    if (!SfxDocTabStyle::IsValidHexColor(rColor))
        return std::nullopt;

    if (rColor.getLength() == 4)
    {
        const sal_uInt8 nRed = lcl_hexDigit(rColor[1]) * 17;
        const sal_uInt8 nGreen = lcl_hexDigit(rColor[2]) * 17;
        const sal_uInt8 nBlue = lcl_hexDigit(rColor[3]) * 17;
        return Color(ColorAlpha, 255, nRed, nGreen, nBlue);
    }

    const sal_uInt8 nRed = lcl_hexByte(rColor, 1);
    const sal_uInt8 nGreen = lcl_hexByte(rColor, 3);
    const sal_uInt8 nBlue = lcl_hexByte(rColor, 5);
    const sal_uInt8 nAlpha = rColor.getLength() == 9 ? lcl_hexByte(rColor, 7) : 255;
    return Color(ColorAlpha, nAlpha, nRed, nGreen, nBlue);
}

// A resolved, already-normalized per-document tab style. Every field is produced
// by passing the untrusted persisted value through SfxDocTabStyle::Normalize, so
// NOTHING the strip renders is a raw registry value or a hardcoded literal.
struct SfxResolvedDocTabStyle
{
    OUString aLabel;                 // CustomLabel (normalized) or frame title fallback
    OUString aCustomLabel;           // Empty means keep following the live frame title
    OUString aBackgroundColor;       // Original normalized spelling for lossless editing
    std::optional<Color> oColor;     // Decoded BackgroundColor, including alpha
    OUString aTextColor;             // Original normalized spelling for lossless editing
    std::optional<Color> oTextColor; // Decoded TextColor, including alpha
    OUString aFontFamily;
    sal_Int16 nFontSize = SfxDocTabStyle::DEFAULT_FONT_SIZE;
    bool bBold = false;
    bool bItalic = false;
    bool bUnderline = false;
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
    else if (sal_Int16 nValue16; aAny >>= nValue16)
        aRaw = OUString::number(nValue16);
    else if (sal_Int32 nValue32; aAny >>= nValue32)
        aRaw = OUString::number(nValue32);
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
    // History/DocumentTabStyles, node-type DocumentTabStyle). A dynamic set
    // has no generated officecfg accessor, so it is opened through the
    // configuration provider exactly as sfx2/source/doc/doctemplates.cxx does.
    uno::Reference<container::XNameAccess> xStyles(lcl_openTabStyleSet(false),
                                                   uno::UNO_QUERY);
    try
    {
        if (!xStyles.is() || !xStyles->hasByName(aUrl))
            return aStyle;

        uno::Reference<container::XNameAccess> xEntry;
        xStyles->getByName(aUrl) >>= xEntry;
        if (!xEntry.is())
            return aStyle;

        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"CustomLabel"); r.bKeep
            && !r.aValue.isEmpty())
        {
            aStyle.aCustomLabel = r.aValue;
            aStyle.aLabel = r.aValue;
        }
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"BackgroundColor");
            r.bKeep)
        {
            aStyle.aBackgroundColor = r.aValue;
            aStyle.oColor = lcl_parseHexColor(r.aValue);
        }
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"TextColor"); r.bKeep)
        {
            aStyle.aTextColor = r.aValue;
            aStyle.oTextColor = lcl_parseHexColor(r.aValue);
        }
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"FontFamily"); r.bKeep)
            aStyle.aFontFamily = r.aValue;
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"FontSize"); r.bKeep)
            aStyle.nFontSize = static_cast<sal_Int16>(r.aValue.toInt32());
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Bold"); r.bKeep)
            aStyle.bBold = r.aValue == u"true";
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Italic"); r.bKeep)
            aStyle.bItalic = r.aValue == u"true";
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Underline"); r.bKeep)
            aStyle.bUnderline = r.aValue == u"true";
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Pinned"); r.bKeep)
            aStyle.bPinned = r.aValue == u"true";
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Favorite"); r.bKeep)
            aStyle.bFavorite = r.aValue == u"true";
        if (SfxDocTabStyle::Result r = lcl_normalizedField(xEntry, u"Order"); r.bKeep)
            aStyle.nOrder = r.aValue.toInt32();
    }
    catch (const uno::Exception&)
    {
        // A frame/config node can disappear while the desktop is closing. The
        // neutral title/default style remains safe and the next refresh drops it.
    }

    return aStyle;
}
} // namespace

bool SfxDocumentTabBar::IsTabsEnabled()
{
    // Stage-2 officecfg group; default false. This is the fail-closed guard: when
    // false the strip is never constructed and reserves no frame layout space.
    try
    {
        return officecfg::Office::Common::DocumentTabs::TabsEnabled::get();
    }
    catch (const uno::Exception&)
    {
        return false;
    }
}

bool SfxDocumentTabBar::ShouldShow()
{
    return IsTabsEnabled() && lcl_materialThemeEnvActive()
           && !Application::GetSettings().GetStyleSettings().GetHighContrastMode();
}

VclPtr<SfxDocumentTabBar>
SfxDocumentTabBar::Create(vcl::Window* pParent,
                          const uno::Reference<frame::XFrame>& xOwnerFrame)
{
    // The single construction seam. If tabs are disabled, return nullptr so no
    // widget exists, nothing is shown, and no frame layout space is reserved.
    // The strip is also inert unless the Material theme is
    // active, but the hard cannot-construct gate is TabsEnabled.
    if (!IsTabsEnabled())
        return nullptr;
    if (!ShouldShow() || !pParent || !xOwnerFrame.is())
        return nullptr;

    VclPtr<SfxDocumentTabBar> pBar
        = VclPtr<SfxDocumentTabBar>::Create(pParent, xOwnerFrame);
    pBar->Rebuild();
    return pBar;
}

SfxDocumentTabBar::SfxDocumentTabBar(
    vcl::Window* pParent, const uno::Reference<frame::XFrame>& xOwnerFrame)
    : TabBar(pParent, WB_3DLOOK | WB_MINSCROLL | WB_SCROLL | WB_RANGESELECT | WB_DRAG, true)
    , mxOwnerFrame(xOwnerFrame)
    , mnLargestFontSize(SfxDocTabStyle::DEFAULT_FONT_SIZE)
{
}

SfxDocumentTabBar::~SfxDocumentTabBar() { disposeOnce(); }

void SfxDocumentTabBar::dispose()
{
    maEntries.clear();
    maMaterialTabColors.clear();
    mxOwnerFrame.clear();
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
    mnLargestFontSize = SfxDocTabStyle::DEFAULT_FONT_SIZE;

    // Gather (frame, resolved style) pairs, then arrange by Pinned then Order --
    // both driven entirely by the persisted SfxDocTabStyle, nothing hardcoded.
    struct Row { uno::Reference<frame::XFrame> xFrame; SfxResolvedDocTabStyle aStyle; };
    std::vector<Row> aRows;
    for (SfxFrame* pFrame = SfxFrame::GetFirst(); pFrame;
         pFrame = SfxFrame::GetNext(*pFrame))
    {
        // The SfxFrame registry is the authoritative product-lifetime list.
        // Unlike Desktop::getFrames(), it lets close synchronization exclude a
        // wrapper as soon as its destructor removes it, even if a UNO frame
        // reference has not reached its final disposal callback yet.
        if (pFrame->IsClosing_Impl() || pFrame->IsInPlace()
            || pFrame->IsMarkedHidden_Impl()
            || !pFrame->GetCurrentDocument())
            continue;
        const uno::Reference<frame::XFrame> xFrame = pFrame->GetFrameInterface();
        if (!lcl_isLiveDocumentFrame(xFrame))
            continue;
        aRows.push_back({ xFrame, lcl_resolveStyle(xFrame) });
    }
    std::stable_sort(aRows.begin(), aRows.end(), [](const Row& a, const Row& b) {
        if (a.aStyle.bPinned != b.aStyle.bPinned)
            return a.aStyle.bPinned; // pinned tabs lead
        if (a.aStyle.bFavorite != b.aStyle.bFavorite)
            return a.aStyle.bFavorite; // favourites lead within pin state
        return a.aStyle.nOrder < b.aStyle.nOrder;
    });

    sal_uInt16 nPageId = 1;
    for (const Row& rRow : aRows)
    {
        // Favourite is a real, visible style: it leads within the pin group and
        // receives a text/accessibility marker instead of being inert config.
        const OUString aRenderedLabel
            = rRow.aStyle.bFavorite ? u"\u2605 "_ustr + rRow.aStyle.aLabel
                                    : rRow.aStyle.aLabel;
        InsertPage(nPageId, aRenderedLabel);
        if (rRow.aStyle.oColor)
            SetMaterialAwareTabBgColor(nPageId, *rRow.aStyle.oColor);

        vcl::Font aPageFont = GetFont();
        if (!rRow.aStyle.aFontFamily.isEmpty())
            aPageFont.SetFamilyName(rRow.aStyle.aFontFamily);
        const Size aFontPixels = GetOutDev()->LogicToPixel(
            Size(0, rRow.aStyle.nFontSize), MapMode(MapUnit::MapPoint));
        aPageFont.SetFontHeight(aFontPixels.Height());
        aPageFont.SetWeight(rRow.aStyle.bBold ? WEIGHT_BOLD : WEIGHT_NORMAL);
        aPageFont.SetItalic(rRow.aStyle.bItalic ? FontItalic::ITALIC_NORMAL
                                                : FontItalic::ITALIC_NONE);
        aPageFont.SetUnderline(rRow.aStyle.bUnderline ? LINESTYLE_SINGLE
                                                      : LINESTYLE_NONE);
        SetPageFont(nPageId, aPageFont);
        if (rRow.aStyle.oTextColor)
            SetPageTextColor(nPageId, *rRow.aStyle.oTextColor);

        maEntries.push_back({ nPageId, rRow.xFrame });
        mnLargestFontSize = std::max(mnLargestFontSize, rRow.aStyle.nFontSize);
        ++nPageId;
    }

    const sal_Int16 nTabWidth = lcl_tabWidthSetting();
    const tools::Long nWidthPixels
        = static_cast<tools::Long>((nTabWidth == 0 ? 160 : nTabWidth == 2 ? 320 : 240)
                                  * GetDPIScaleFactor());
    SetMaxPageWidth(nWidthPixels);
    SelectOwnerFrame();
}

tools::Long SfxDocumentTabBar::GetPreferredHeight() const
{
    const Size aFontPixels = GetOutDev()->LogicToPixel(
        Size(0, mnLargestFontSize), MapMode(MapUnit::MapPoint));
    const bool bCompact = lcl_tabDensitySetting() == 1;
    const tools::Long nPadding
        = static_cast<tools::Long>((bCompact ? 6 : 10) * GetDPIScaleFactor());
    return std::max(CalcWindowSizePixel().Height(), aFontPixels.Height() + nPadding);
}

uno::Reference<frame::XFrame> SfxDocumentTabBar::FrameForPage(sal_uInt16 nPageId) const
{
    for (const TabEntry& rEntry : maEntries)
        if (rEntry.nPageId == nPageId)
            return rEntry.xFrame;
    return uno::Reference<frame::XFrame>();
}

void SfxDocumentTabBar::SelectOwnerFrame()
{
    for (const TabEntry& rEntry : maEntries)
    {
        if (rEntry.xFrame == mxOwnerFrame)
        {
            SetCurPageId(rEntry.nPageId);
            MakeVisible(rEntry.nPageId);
            return;
        }
    }
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
    try
    {
        VclPtr<vcl::Window> pWin = VCLUnoHelper::GetWindow(xFrame->getContainerWindow());
        if (!pWin)
        {
            Rebuild();
            return;
        }
        pWin->GrabFocus();
        pWin->ToTop(ToTopFlags::RestoreWhenMin);
    }
    catch (const uno::Exception&)
    {
        // A close can race a click. Drop the disposed reference instead of
        // dereferencing it again or leaving a stale selectable page behind.
        Rebuild();
    }
}

void SfxDocumentTabBar::Select()
{
    // Activation of a tab raises the bound document window; it does NOT reparent
    // or re-host any frame (that would be true in-window hosting, deferred).
    const sal_uInt16 nSelectedPage = GetCurPageId();
    RaiseFrameForPage(nSelectedPage);
    SelectOwnerFrame();
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
    std::unique_ptr<weld::Entry> xTextColor(xBuilder->weld_entry(u"textcolor"_ustr));
    std::unique_ptr<weld::Entry> xFontFamily(xBuilder->weld_entry(u"fontfamily"_ustr));
    std::unique_ptr<weld::CheckButton> xPinned(xBuilder->weld_check_button(u"pinned"_ustr));
    std::unique_ptr<weld::CheckButton> xFavorite(xBuilder->weld_check_button(u"favorite"_ustr));
    std::unique_ptr<weld::CheckButton> xBold(xBuilder->weld_check_button(u"bold"_ustr));
    std::unique_ptr<weld::CheckButton> xItalic(xBuilder->weld_check_button(u"italic"_ustr));
    std::unique_ptr<weld::CheckButton> xUnderline(
        xBuilder->weld_check_button(u"underline"_ustr));
    std::unique_ptr<weld::SpinButton> xFontSize(xBuilder->weld_spin_button(u"fontsize"_ustr));

    const SfxResolvedDocTabStyle aStyle = lcl_resolveStyle(xFrame);
    if (xLabel)
        xLabel->set_text(aStyle.aCustomLabel);
    if (xColor)
        xColor->set_text(aStyle.aBackgroundColor);
    if (xTextColor)
        xTextColor->set_text(aStyle.aTextColor);
    if (xFontFamily)
        xFontFamily->set_text(aStyle.aFontFamily);
    if (xPinned)
        xPinned->set_active(aStyle.bPinned);
    if (xFavorite)
        xFavorite->set_active(aStyle.bFavorite);
    if (xBold)
        xBold->set_active(aStyle.bBold);
    if (xItalic)
        xItalic->set_active(aStyle.bItalic);
    if (xUnderline)
        xUnderline->set_active(aStyle.bUnderline);
    if (xFontSize)
        xFontSize->set_value(aStyle.nFontSize);

    if (xDialog->run() != RET_OK)
        return;

    // Persist through the configuration, each value re-validated by the stage-2
    // normalizer before it is written so the dialog cannot inject an unsafe
    // style. The set is opened writable and committed via XChangesBatch.
    try
    {
        uno::Reference<uno::XInterface> xSet(lcl_openTabStyleSet(true));
        uno::Reference<container::XNameContainer> xStyles(xSet, uno::UNO_QUERY_THROW);

        uno::Reference<beans::XPropertySet> xEntry;
        if (xStyles->hasByName(aUrl))
        {
            xStyles->getByName(aUrl) >>= xEntry;
        }
        else
        {
            // Dynamic configuration sets do not materialise their first member
            // automatically. Create the template node, then insert it by URL.
            uno::Reference<lang::XSingleServiceFactory> xFactory(xStyles,
                                                                  uno::UNO_QUERY_THROW);
            xEntry.set(xFactory->createInstance(), uno::UNO_QUERY_THROW);
            xStyles->insertByName(aUrl, uno::Any(xEntry));
        }
        if (!xEntry.is())
            return;

        const auto setNormalizedString
            = [&xEntry](std::u16string_view aKey, const OUString& rRaw) {
                  SfxDocTabStyle::Result r = SfxDocTabStyle::Normalize(aKey, rRaw);
                  xEntry->setPropertyValue(OUString(aKey),
                                           uno::Any(r.bKeep ? r.aValue : OUString()));
              };

        if (xLabel)
            setNormalizedString(u"CustomLabel", xLabel->get_text());
        if (xColor)
            setNormalizedString(u"BackgroundColor", xColor->get_text());
        if (xTextColor)
            setNormalizedString(u"TextColor", xTextColor->get_text());
        if (xFontFamily)
            setNormalizedString(u"FontFamily", xFontFamily->get_text());
        if (xPinned)
            xEntry->setPropertyValue(u"Pinned"_ustr, uno::Any(xPinned->get_active()));
        if (xFavorite)
            xEntry->setPropertyValue(u"Favorite"_ustr, uno::Any(xFavorite->get_active()));
        if (xBold)
            xEntry->setPropertyValue(u"Bold"_ustr, uno::Any(xBold->get_active()));
        if (xItalic)
            xEntry->setPropertyValue(u"Italic"_ustr, uno::Any(xItalic->get_active()));
        if (xUnderline)
            xEntry->setPropertyValue(u"Underline"_ustr,
                                     uno::Any(xUnderline->get_active()));
        if (xFontSize)
        {
            SfxDocTabStyle::Result r = SfxDocTabStyle::Normalize(
                u"FontSize", OUString::number(xFontSize->get_value()));
            xEntry->setPropertyValue(
                u"FontSize"_ustr,
                uno::Any(static_cast<sal_Int16>(
                    r.bKeep ? r.aValue.toInt32() : SfxDocTabStyle::DEFAULT_FONT_SIZE)));
        }

        if (uno::Reference<util::XChangesBatch> xBatch{ xSet, uno::UNO_QUERY };
            xBatch.is())
        {
            xBatch->commitChanges();
        }
    }
    catch (const uno::Exception&)
    {
        return;
    }

    // Every frame owns a copy of the global document strip; keep them all on
    // the same committed configuration snapshot.
    SfxFrame::RefreshDocumentTabBars_Impl();
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
