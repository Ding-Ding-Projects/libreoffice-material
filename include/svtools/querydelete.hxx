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
#pragma once

#include <config_options.h>
#include <memory>
#include <vcl/vclenum.hxx>
#include <vcl/weld/Button.hxx>
#include <vcl/weld/DialogController.hxx>
#include <svtools/svtdllapi.h>

namespace svtools
{
// QueryDeleteDlg_Impl

enum QueryDeleteResult_Impl
{
    QUERYDELETE_YES = RET_YES,
    QUERYDELETE_ALL = 101
};

class UNLESS_MERGELIBS_MORE(SVT_DLLPUBLIC) QueryDeleteDlg_Impl final
    : public weld::MessageDialogController
{
private:
    std::unique_ptr<weld::Button> m_xAllButton;

    // "Delete All" is a bulk escalation of the primary action, not one of the
    // standard footer responses the Material dialog anatomy declares
    // (docs/design/08-dialogs.md 8.1), so it is not an .ui <action-widget>:
    // it reports QUERYDELETE_ALL from its own click handler instead.
    DECL_LINK(AllHdl, weld::Button&, void);

public:
    QueryDeleteDlg_Impl(weld::Widget* pParent, std::u16string_view rName);
    virtual ~QueryDeleteDlg_Impl() override;

    void EnableAllButton() { m_xAllButton->set_sensitive(true); }
};
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
