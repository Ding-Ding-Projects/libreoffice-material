/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4; fill-column: 100 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include "NotificationOverlayWindow.hxx"

#include <vcl/vclevent.hxx>
#include <vcl/weld/Container.hxx>
#include <vcl/window.hxx>

#include <algorithm>

namespace sfx2
{
NotificationOverlayWindow::NotificationOverlayWindow(vcl::Window* pParent, const OUString& rUIFile,
                                                     const OUString& rId, bool bAllowCycleFocusOut)
    : InterimItemWindow(pParent, rUIFile, rId, bAllowCycleFocusOut)
    , m_pObservedParent(pParent)
{
    InitControlBase(m_xContainer.get());
    if (m_pObservedParent)
        m_pObservedParent->AddEventListener(
            LINK(this, NotificationOverlayWindow, ParentEventHdl));
}

NotificationOverlayWindow::~NotificationOverlayWindow() { disposeOnce(); }

void NotificationOverlayWindow::dispose()
{
    if (m_pObservedParent)
    {
        m_pObservedParent->RemoveEventListener(
            LINK(this, NotificationOverlayWindow, ParentEventHdl));
        m_pObservedParent = nullptr;
    }
    m_aLayoutHdl = Link<NotificationOverlayWindow&, void>();
    InterimItemWindow::dispose();
}

void NotificationOverlayWindow::Resize()
{
    InterimItemWindow::Resize();
    m_aLayoutHdl.Call(*this);
}

void NotificationOverlayWindow::RepositionBottomRight(sal_Int32 nHInset, sal_Int32 nVInset,
                                                      sal_Int32 nDesiredWidth)
{
    m_nHorizontalInset = nHInset;
    m_nVerticalInset = nVInset;
    m_nDesiredWidth = nDesiredWidth;
    m_bAnchored = true;

    vcl::Window* pParent = GetParent();
    if (!pParent)
        return;

    const Size aParent(pParent->GetOutputSizePixel());
    const Size aOptimal(GetOptimalSize());

    tools::Long nWidth = nDesiredWidth > 0 ? nDesiredWidth : aOptimal.Width();
    const tools::Long nWidthBudget = aParent.Width() - 2 * nHInset;
    if (nWidthBudget > 0)
        nWidth = std::min<tools::Long>(nWidth, nWidthBudget);
    nWidth = std::max<tools::Long>(nWidth, 1);

    tools::Long nHeight = std::max<tools::Long>(aOptimal.Height(), 1);
    const tools::Long nHeightBudget = aParent.Height() - 2 * nVInset;
    if (nHeightBudget > 0)
        nHeight = std::min<tools::Long>(nHeight, nHeightBudget);

    tools::Long nX = aParent.Width() - nWidth - nHInset;
    tools::Long nY = aParent.Height() - nHeight - nVInset;
    nX = std::max<tools::Long>(nX, 0);
    nY = std::max<tools::Long>(nY, 0);

    SetPosSizePixel(Point(nX, nY), Size(nWidth, nHeight));
    Show();
    // Raise above siblings without grabbing top-level focus.
    SetZOrder(nullptr, ZOrderFlags::First);
}

IMPL_LINK(NotificationOverlayWindow, ParentEventHdl, VclWindowEvent&, rEvent, void)
{
    if (rEvent.GetId() == VclEventId::ObjectDying)
    {
        m_pObservedParent = nullptr;
        return;
    }

    // A hidden manager must stay hidden. Visible overlays follow their owner's client area without
    // waiting for another snapshot, preference change, or frame-activation event.
    if (rEvent.GetId() == VclEventId::WindowResize && m_bAnchored && IsVisible())
        RepositionBottomRight(m_nHorizontalInset, m_nVerticalInset, m_nDesiredWidth);
}

} // namespace sfx2

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
