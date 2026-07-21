/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#pragma once

#include <sfx2/dllapi.h>
#include <rtl/ustring.hxx>

namespace weld
{
class Widget;
}

namespace sfx2
{
/**
 * Parameters for the shared Material destructive-confirmation dialog.
 *
 * See docs/design/08-dialogs.md 8.1 "Destructive-confirmation pattern". The message states the
 * object and consequence of the irreversible act; the footer keeps the shared order
 * Help | spacer | safe secondary | destructive primary; the destructive button carries the
 * destructive-action role (Material @error-container) and a verb-named label; and both the initial
 * focus and the Enter default bind to the safe action, so Enter/Space activation can never destroy
 * data.
 */
struct DestructiveConfirmation
{
    /// Primary text: names the object of the destructive act (e.g. "Delete the 3 selected sheets?").
    OUString sPrimaryText;
    /// Secondary text: states the consequence and, where one exists, the recovery route. Optional.
    OUString sSecondaryText;
    /// Verb-named destructive button label (e.g. "Overwrite"). Empty keeps the localized default verb
    /// ("Delete") declared in the .ui; it is never a bare "OK"/"Yes".
    OUString sDestructiveLabel;
    /// Safe (secondary) button label. Empty keeps the localized default ("Cancel").
    OUString sSafeLabel;
    /// Optional Help id. Empty hides the Help button.
    OUString sHelpId;
};

/**
 * Present the shared Material destructive-confirmation dialog.
 *
 * @param pParent  the transient parent widget to modally centre over.
 * @param rParams  the message, verb label, and optional help/safe overrides.
 * @return         true iff the user explicitly chose the destructive action; false for the safe
 *                 action, Escape, or the title-row close (no data is committed).
 *
 * The helper wires the safe-by-default keyboard contract itself: callers must not add their own
 * default-response or focus handling. The destructive act must be performed by the caller only when
 * this returns true.
 */
SFX2_DLLPUBLIC bool ConfirmDestructiveAction(weld::Widget* pParent,
                                             const DestructiveConfirmation& rParams);

} // namespace sfx2

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
