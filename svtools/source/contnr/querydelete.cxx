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

#include <svtools/querydelete.hxx>
#include <vcl/weld/Builder.hxx>
#include <vcl/weld/MessageDialog.hxx>

namespace svtools
{
QueryDeleteDlg_Impl::QueryDeleteDlg_Impl(weld::Widget* pParent, std::u16string_view rName)
    : MessageDialogController(pParent, u"svt/ui/querydeletedialog.ui"_ustr,
                              u"QueryDeleteDialog"_ustr)
    , m_xAllButton(m_xBuilder->weld_button(u"all"_ustr))
{
    // "Delete All" keeps returning QUERYDELETE_ALL, but it does so from here
    // rather than from a custom <action-widget response="101"> in the .ui: the
    // Material footer anatomy (docs/design/08-dialogs.md 8.1) declares standard
    // responses only. Callers still compare the run() result against
    // QUERYDELETE_ALL exactly as before.
    m_xAllButton->connect_clicked(LINK(this, QueryDeleteDlg_Impl, AllHdl));
    // display specified texts
    m_xDialog->set_secondary_text(m_xDialog->get_secondary_text().replaceFirst("%s", rName));
}

IMPL_LINK_NOARG(QueryDeleteDlg_Impl, AllHdl, weld::Button&, void)
{
    m_xDialog->response(QUERYDELETE_ALL);
}

QueryDeleteDlg_Impl::~QueryDeleteDlg_Impl() {}
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
