/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 * This file incorporates work covered by the following license notice:
 *
 *   Licensed to the Apache Software Foundation (ASF) under one or more
 *   contributor license agreements. See the NOTICE file distributed
 *   with this work for additional information regarding copyright
 *   ownership. The ASF licenses this file to you under the Apache
 *   License, Version 2.0 (the "License"); you may not use this file
 *   except in compliance with the License. You may obtain a copy of
 *   the License at http://www.apache.org/licenses/LICENSE-2.0 .
 */

#include <scalectrl.hxx>

#include <vcl/commandevent.hxx>
#include <vcl/MaterialTokens.hxx>
#include <vcl/settings.hxx>
#include <vcl/status.hxx>
#include <vcl/svapp.hxx>
#include <vcl/weld/Builder.hxx>
#include <vcl/weld/Menu.hxx>
#include <vcl/weld/Window.hxx>
#include <vcl/weld/weldutils.hxx>
#include <sfx2/bindings.hxx>
#include <sfx2/viewfrm.hxx>
#include <svl/stritem.hxx>
#include <sfx2/sfxsids.hrc>

#include <ViewShellBase.hxx>
#include <drawdoc.hxx>
#include <app.hrc>

#include <cstdlib>
#include <optional>
#include <string_view>
#include <sdresid.hxx>
#include <strings.hrc>

#define TABLE_COUNT 9

namespace
{
// Resolve the Material @on-surface-variant token for the status-bar scale text,
// but only when the Material file-widget theme is the active, documented
// activation (VCL_FILE_WIDGET_THEME=material, per the docs/design/11-impress-draw.md
// verification checkpoints). Under the default/native theme this returns nothing,
// so the zoom control never touches the status-bar foreground and existing
// behavior is preserved. The value flows through vcl::MaterialTokens -- the single
// named-token table over definition.xml -- rather than any raw color literal.
std::optional<Color> lcl_getMaterialStatusTextColor()
{
    const char* pThemeName = std::getenv("VCL_FILE_WIDGET_THEME");
    if (!pThemeName || std::string_view(pThemeName) != "material")
        return std::nullopt;

    const bool bDark = Application::GetSettings().GetStyleSettings().GetWindowColor().IsDark();
    const vcl::MaterialTokens aTokens
        = vcl::MaterialTokens::fromThemeDefinition(bDark ? "dark"_ostr : OString());
    if (!aTokens.isValid())
        return std::nullopt;
    return aTokens.findColor("on-surface-variant");
}
}

SFX_IMPL_STATUSBAR_CONTROL(SdScaleControl, SfxStringItem);

// class SdScaleControl ------------------------------------------
SdScaleControl::SdScaleControl(sal_uInt16 _nSlotId, sal_uInt16 _nId, StatusBar& rStb)
    : SfxStatusBarControl(_nSlotId, _nId, rStb)
{
    GetStatusBar().SetQuickHelpText(GetId(), SdResId(STR_SCALE_TOOLTIP));
}

SdScaleControl::~SdScaleControl() {}

void SdScaleControl::StateChangedAtStatusBarControl(sal_uInt16 /*nSID*/, SfxItemState eState,
                                                    const SfxPoolItem* pState)
{
    if (eState != SfxItemState::DEFAULT || SfxItemState::DISABLED == eState)
        return;

    auto pStringItem = dynamic_cast<const SfxStringItem*>(pState);
    if (!pStringItem)
    {
        SAL_WARN("sd", "Item wasn't a SfxStringItem");
        return;
    }
    GetStatusBar().SetItemText(GetId(), pStringItem->GetValue());

    // When the Material theme is active, paint the scale text in the Material
    // @on-surface-variant token obtained from the token accessor; inert otherwise.
    if (const std::optional<Color> oColor = lcl_getMaterialStatusTextColor())
        GetStatusBar().SetControlForeground(*oColor);
}

void SdScaleControl::Command(const CommandEvent& rCEvt)
{
    if (rCEvt.GetCommand() != CommandEventId::ContextMenu
        || GetStatusBar().GetItemText(GetId()).isEmpty())
        return;

    SfxViewFrame* pViewFrame = SfxViewFrame::Current();

    sd::ViewShellBase* pViewShellBase = sd::ViewShellBase::GetViewShellBase(pViewFrame);
    if (!pViewShellBase)
        return;

    SdDrawDocument* pDoc = pViewShellBase->GetDocument();
    if (!pDoc)
        return;

    std::unique_ptr<weld::Builder> xBuilder(
        Application::CreateBuilder(nullptr, u"modules/simpress/ui/masterpagemenu.ui"_ustr));
    std::unique_ptr<weld::Menu> xPopup(xBuilder->weld_menu(u"menu"_ustr));

    sal_uInt16 aTable[TABLE_COUNT] = { 1, 2, 5, 10, 12, 24, 48, 50, 100 };

    for (sal_uInt16 i = TABLE_COUNT - 1; i > 0; i--)
        xPopup->append(OUString::number(TABLE_COUNT - i), OUString::number(aTable[i]) + ":1");
    for (sal_uInt16 i = 0; i < TABLE_COUNT; i++)
        xPopup->append(OUString::number(TABLE_COUNT + i), "1:" + OUString::number(aTable[i]));

    ::tools::Rectangle aRect(rCEvt.GetMousePosPixel(), Size(1, 1));
    weld::Window* pParent = weld::GetPopupParent(GetStatusBar(), aRect);
    OUString sResult = xPopup->popup_at_rect(pParent, aRect);
    if (sResult.isEmpty())
        return;

    sal_Int32 i = sResult.toUInt32();
    sal_Int32 nX;
    sal_Int32 nY;
    if (i > TABLE_COUNT - 1)
        nX = 1;
    else
        nX = aTable[(TABLE_COUNT - i) % TABLE_COUNT];
    if (i > TABLE_COUNT - 1)
        nY = aTable[i % TABLE_COUNT];
    else
        nY = 1;
    pDoc->SetUIScale(double(nX) / nY);

    SfxBindings& pBindings = pViewFrame->GetBindings();
    pBindings.Invalidate(SID_SCALE); //update statusbar
    pBindings.Invalidate(SID_ATTR_METRIC); //update sidebar
    pViewShellBase->UpdateBorder(true); // update ruler
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
