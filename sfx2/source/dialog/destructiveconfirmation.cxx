/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <sfx2/destructiveconfirmation.hxx>

#include <vcl/svapp.hxx>
#include <vcl/vclenum.hxx>
#include <vcl/weld/Builder.hxx>
#include <vcl/weld/Button.hxx>
#include <vcl/weld/MessageDialog.hxx>

#include <memory>

namespace sfx2
{
bool ConfirmDestructiveAction(weld::Widget* pParent, const DestructiveConfirmation& rParams)
{
    std::unique_ptr<weld::Builder> xBuilder(
        Application::CreateBuilder(pParent, u"sfx/ui/materialdestructiveconfirmdialog.ui"_ustr));
    std::unique_ptr<weld::MessageDialog> xDialog(
        xBuilder->weld_message_dialog(u"MaterialDestructiveConfirmDialog"_ustr));

    // The message states the object of the destructive act and its consequence/recovery.
    xDialog->set_primary_text(rParams.sPrimaryText);
    xDialog->set_secondary_text(rParams.sSecondaryText);

    // Destructive primary: verb-named label and the destructive-action role (Material
    // @error-container) declared on this button in the .ui. Keep the localized default verb when the
    // caller supplies none; never fall back to a bare "OK".
    std::unique_ptr<weld::Button> xDestructive(xBuilder->weld_button(u"destructive"_ustr));
    if (!rParams.sDestructiveLabel.isEmpty())
        xDestructive->set_label(rParams.sDestructiveLabel);

    // Safe secondary: optional caller label; this is the action Escape and the title-row close map
    // to as well.
    std::unique_ptr<weld::Button> xSafe(xBuilder->weld_button(u"safe"_ustr));
    if (!rParams.sSafeLabel.isEmpty())
        xSafe->set_label(rParams.sSafeLabel);

    // Help stays hidden unless the caller wires a topic; footer keeps the shared
    // Help | spacer | safe | destructive order.
    std::unique_ptr<weld::Button> xHelp(xBuilder->weld_button(u"help"_ustr));
    if (!rParams.sHelpId.isEmpty())
    {
        xHelp->set_help_id(rParams.sHelpId);
        xHelp->show();
    }
    else
    {
        xHelp->hide();
    }

    // Safe-by-default keyboard contract: the Enter default AND the initial focus both bind to the
    // safe action, so Enter/Space activation cannot destroy data. The destructive action always
    // requires explicit navigation. (Keyboard-default emphasis beyond this remains deferred per
    // MATERIAL_DESIGN.md milestone 10.)
    xDialog->set_default_response(RET_CANCEL);
    xSafe->grab_focus();

    return xDialog->run() == RET_OK;
}

} // namespace sfx2

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
