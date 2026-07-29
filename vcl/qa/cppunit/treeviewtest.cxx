/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4; fill-column: 100 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <salinst.hxx>
#include <salvtables.hxx>
#include <svdata.hxx>

#include <com/sun/star/accessibility/AccessibleStateType.hpp>
#include <com/sun/star/accessibility/XAccessible.hpp>
#include <com/sun/star/accessibility/XAccessibleSelection.hpp>
#include <comphelper/OAccessible.hxx>
#include <cppuhelper/implbase.hxx>
#include <test/bootstrapfixture.hxx>
#include <vcl/builder.hxx>
#include <vcl/event.hxx>
#include <vcl/toolkit/button.hxx>
#include <vcl/weld/Builder.hxx>
#include <vcl/weld/TreeView.hxx>

class TreeViewTest : public test::BootstrapFixture
{
public:
    TreeViewTest()
        : BootstrapFixture(true, false)
    {
    }

    void setUp() override;
    void tearDown() override;

    void testIterPrevious();
    void testInsensitiveRowIsNotSelectable();
    void testSuggestedActionClassSetsPushButtonAction();

    CPPUNIT_TEST_SUITE(TreeViewTest);
    CPPUNIT_TEST(testIterPrevious);
    CPPUNIT_TEST(testInsensitiveRowIsNotSelectable);
    CPPUNIT_TEST(testSuggestedActionClassSetsPushButtonAction);
    CPPUNIT_TEST_SUITE_END();

private:
    std::unique_ptr<weld::Builder> m_xBuilder;
    std::unique_ptr<weld::TreeView> m_xTreeView;
};

void TreeViewTest::setUp()
{
    test::BootstrapFixture::setUp();

    OUString sDataDir = m_directories.getURLFromSrc(u"vcl/qa/cppunit/data/");

    SalInstance* pSalInstance = GetSalInstance();
    m_xBuilder = pSalInstance->CreateBuilder(nullptr, sDataDir, u"treeviewtest.ui"_ustr);
    m_xTreeView = m_xBuilder->weld_tree_view(u"treeview"_ustr);
}

void TreeViewTest::tearDown()
{
    m_xTreeView.reset();
    m_xBuilder.reset();

    test::BootstrapFixture::tearDown();
}

// Test that iter_previous works when the previous node has children on demand. See tdf#172670
void TreeViewTest::testIterPrevious()
{
    // Create the first node with children on demand
    m_xTreeView->append_text(u"first"_ustr);
    std::unique_ptr<weld::TreeIter> xIter = m_xTreeView->make_iterator();
    m_xTreeView->get_iter_first(*xIter);
    m_xTreeView->set_children_on_demand(*xIter, true);

    // Add a regular second node
    m_xTreeView->append_text(u"second"_ustr);

    // Point the iterator to the second node
    m_xTreeView->iter_next(*xIter);
    CPPUNIT_ASSERT_EQUAL(u"second"_ustr, m_xTreeView->get_text(*xIter));

    // Move back to the first node. Without the fix this will do an infinite recursion with stack
    // overflow.
    m_xTreeView->iter_previous(*xIter);
    CPPUNIT_ASSERT_EQUAL(u"first"_ustr, m_xTreeView->get_text(*xIter));
}

void TreeViewTest::testInsensitiveRowIsNotSelectable()
{
    m_xTreeView->append_text(u"first"_ustr);
    m_xTreeView->append_text(u"disabled"_ustr);
    m_xTreeView->append_text(u"third"_ustr);
    m_xTreeView->set_selection_mode(SelectionMode::Multiple);

    m_xTreeView->select(0);
    m_xTreeView->select(1);
    CPPUNIT_ASSERT(m_xTreeView->is_selected(0));
    CPPUNIT_ASSERT(m_xTreeView->is_selected(1));

    // Disabling a whole row clears only that row's existing selection and blocks direct and bulk
    // selection without disturbing another selected row.
    m_xTreeView->set_sensitive(1, false);
    CPPUNIT_ASSERT(m_xTreeView->is_selected(0));
    CPPUNIT_ASSERT(!m_xTreeView->is_selected(1));
    m_xTreeView->select(1);
    CPPUNIT_ASSERT(!m_xTreeView->is_selected(1));

    auto* pSalTreeView = dynamic_cast<SalInstanceTreeView*>(m_xTreeView.get());
    CPPUNIT_ASSERT(pSalTreeView);
    SvTabListBox& rTreeView = pSalTreeView->getTreeView();
    rTreeView.SetSizePixel(Size(320, 120));
    SvTreeListEntry* pDisabledEntry = rTreeView.GetEntry(1);
    CPPUNIT_ASSERT(pDisabledEntry);
    const Point aDisabledRowCenter = rTreeView.GetBoundingRect(*pDisabledEntry).Center();
    const MouseEvent aDisabledRowClick(aDisabledRowCenter, 1, MouseEventModifiers::SIMPLECLICK,
                                       MOUSE_LEFT);
    rTreeView.MouseButtonDown(aDisabledRowClick);
    CPPUNIT_ASSERT(m_xTreeView->is_selected(0));
    CPPUNIT_ASSERT(!m_xTreeView->is_selected(2));

    m_xTreeView->select_all();
    CPPUNIT_ASSERT(std::vector<int>({ 0, 2 }) == m_xTreeView->get_selected_rows());

    std::unique_ptr<weld::TreeIter> xDisabled = m_xTreeView->get_iterator(1);
    CPPUNIT_ASSERT(xDisabled);
    CPPUNIT_ASSERT(!m_xTreeView->get_sensitive(*xDisabled, -1));

    // The accessibility object must expose the same contract and cannot select the row through
    // XAccessibleSelection because SvTreeListBox rejects non-selectable entries.
    rtl::Reference<comphelper::OAccessible> xAccessible
        = pSalTreeView->getTreeView().GetAccessible();
    CPPUNIT_ASSERT(xAccessible.is());
    css::uno::Reference<css::accessibility::XAccessible> xDisabledAccessible
        = xAccessible->getAccessibleChild(1);
    CPPUNIT_ASSERT(xDisabledAccessible.is());
    const sal_Int64 nStates
        = xDisabledAccessible->getAccessibleContext()->getAccessibleStateSet();
    CPPUNIT_ASSERT_EQUAL(
        sal_Int64(0),
        nStates & css::accessibility::AccessibleStateType::SELECTABLE);
    css::uno::Reference<css::accessibility::XAccessibleSelection> xAccessibleSelection(
        xAccessible->getXWeak(), css::uno::UNO_QUERY_THROW);
    xAccessibleSelection->selectAccessibleChild(1);
    CPPUNIT_ASSERT(!m_xTreeView->is_selected(1));

    m_xTreeView->set_sensitive(1, true);
    CPPUNIT_ASSERT(m_xTreeView->get_sensitive(*xDisabled, -1));
    m_xTreeView->select(1);
    CPPUNIT_ASSERT(m_xTreeView->is_selected(1));
}

void TreeViewTest::testSuggestedActionClassSetsPushButtonAction()
{
    OUString sDataDir = m_directories.getURLFromSrc(u"vcl/qa/cppunit/data/");
    VclBuilder aBuilder(nullptr, sDataDir, u"suggestedaction.ui"_ustr);

    PushButton* pSuggestedAction = aBuilder.get<PushButton>(u"suggested"_ustr);
    PushButton* pPlainButton = aBuilder.get<PushButton>(u"plain"_ustr);
    CPPUNIT_ASSERT(pSuggestedAction);
    CPPUNIT_ASSERT(pPlainButton);
    CPPUNIT_ASSERT(pSuggestedAction->isAction());
    CPPUNIT_ASSERT(!pPlainButton->isAction());
}

CPPUNIT_TEST_SUITE_REGISTRATION(TreeViewTest);

CPPUNIT_PLUGIN_IMPLEMENT();

/* vim:set shiftwidth=4 softtabstop=4 expandtab cinoptions=b1,g0,N-s cinkeys+=0=break: */
