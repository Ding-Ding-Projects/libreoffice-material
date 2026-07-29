# -*- tab-width: 4; indent-tabs-mode: nil; py-indent-offset: 4 -*-
#
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from uitest.framework import UITestCase
from libreoffice.uno.propertyvalue import mkPropertyValues
from uitest.uihelper.common import get_state_as_dict
from uitest.uihelper.common import select_pos

class autocorrectOptions(UITestCase):

    def replace_text(self, control, text):
        control.executeAction("TYPE", mkPropertyValues({"KEYCODE": "CTRL+A"}))
        control.executeAction("TYPE", mkPropertyValues({"KEYCODE": "BACKSPACE"}))
        if text:
            control.executeAction("TYPE", mkPropertyValues({"TEXT": text}))

    def find_tree_row(self, tree, text):
        for child_name in tree.getChildren():
            row = tree.getChild(child_name)
            if get_state_as_dict(row)["Text"] == text:
                return row
        return None

    def select_nonempty_language(self, language, trees):
        state = get_state_as_dict(language)
        current = state["SelectedText"]
        count = int(state["EntryCount"])
        for position in range(count):
            select_pos(language, str(position))
            if get_state_as_dict(language)["SelectedText"] == current:
                continue
            for tree in trees:
                if tree.getChildren():
                    return tree
        return None

    def test_autocorrect_options_writer(self):
        with self.ui_test.create_doc_in_start_center("writer"):

            with self.ui_test.execute_dialog_through_command(".uno:AutoCorrectDlg", close_button="cancel") as xDialog:
                xTabs = xDialog.getChild("tabcontrol")
                select_pos(xTabs, "0")       #tab replace
                origtext = xDialog.getChild("origtext")
                newtext = xDialog.getChild("newtext")
                xnew = xDialog.getChild("new")
                xdelete = xDialog.getChild("delete")
                xtabview = xDialog.getChild("tabview")
                nrRows = get_state_as_dict(xtabview)["VisibleCount"]

                self.assertTrue(int(nrRows) > 0)

                #add new rule
                origtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"CTRL+A"}))
                origtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"BACKSPACE"}))
                origtext.executeAction("TYPE", mkPropertyValues({"TEXT":"::::"}))
                newtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"CTRL+A"}))
                newtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"BACKSPACE"}))
                newtext.executeAction("TYPE", mkPropertyValues({"TEXT":"dvojtecky"}))
                xnew.executeAction("CLICK", tuple())
                nrRowsNew = get_state_as_dict(xtabview)["VisibleCount"]
                nrRowsDiff = int(nrRowsNew) - int(nrRows)
                self.assertEqual(nrRowsDiff, 1)  #we have +1 rule
                #delete rule
                origtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"CTRL+A"}))
                origtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"BACKSPACE"}))
                origtext.executeAction("TYPE", mkPropertyValues({"TEXT":"::::"}))
                newtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"CTRL+A"}))
                newtext.executeAction("TYPE", mkPropertyValues({"KEYCODE":"BACKSPACE"}))
                newtext.executeAction("TYPE", mkPropertyValues({"TEXT":"dvojtecky"}))
                xdelete.executeAction("CLICK", tuple())
                self.assertEqual(get_state_as_dict(xtabview)["VisibleCount"], nrRows)   #we have default nr of rules

                select_pos(xTabs, "1")     #tab Exceptions
                #abbreviations
                abbrev = xDialog.getChild("abbrev")
                newabbrev = xDialog.getChild("newabbrev")
                delabbrev = xDialog.getChild("delabbrev")
                abbrevlist = xDialog.getChild("abbrevlist")

                nrRowsAbb = get_state_as_dict(abbrevlist)["VisibleCount"]

                self.assertTrue(int(nrRowsAbb) > 0)

                abbrev.executeAction("TYPE", mkPropertyValues({"KEYCODE":"CTRL+A"}))
                abbrev.executeAction("TYPE", mkPropertyValues({"KEYCODE":"BACKSPACE"}))
                abbrev.executeAction("TYPE", mkPropertyValues({"TEXT":"qqqqq"}))
                newabbrev.executeAction("CLICK", tuple())
                nrRowsAbbNew = get_state_as_dict(abbrevlist)["VisibleCount"]
                nrRowsAbbDiff = int(nrRowsAbbNew) - int(nrRowsAbb)
                self.assertEqual(nrRowsAbbDiff, 1)  #we have +1 rule
                delabbrev.executeAction("CLICK", tuple())
                self.assertEqual(get_state_as_dict(abbrevlist)["VisibleCount"], nrRowsAbb)   #we have default nr of rules

                #words with two initial capitals
                double = xDialog.getChild("double")
                newdouble = xDialog.getChild("newdouble")
                deldouble = xDialog.getChild("deldouble")
                doublelist = xDialog.getChild("doublelist")

                nrRowsDouble = get_state_as_dict(doublelist)["VisibleCount"]

                self.assertTrue(int(nrRowsDouble) > 0)

                double.executeAction("TYPE", mkPropertyValues({"KEYCODE":"CTRL+A"}))
                double.executeAction("TYPE", mkPropertyValues({"KEYCODE":"BACKSPACE"}))
                double.executeAction("TYPE", mkPropertyValues({"TEXT":"QQqqq"}))
                newdouble.executeAction("CLICK", tuple())
                nrRowsDoubleNew = get_state_as_dict(doublelist)["VisibleCount"]
                nrRowsDoubleDiff = int(nrRowsDoubleNew) - int(nrRowsDouble) #convert string and
                self.assertEqual(nrRowsDoubleDiff, 1)  #we have +1 rule
                deldouble.executeAction("CLICK", tuple())
                self.assertEqual(get_state_as_dict(doublelist)["VisibleCount"], nrRowsDouble)   #we have default nr of rules

    def test_search_filter_keeps_rules_non_actionable_after_rebuilds(self):
        with self.ui_test.create_doc_in_start_center("writer"):
            with self.ui_test.execute_dialog_through_command(
                    ".uno:AutoCorrectDlg", close_button="cancel") as xDialog:
                tabs = xDialog.getChild("tabcontrol")
                search = xDialog.getChild("searchEntry")
                language = xDialog.getChild("lang")

                select_pos(tabs, "0")  # Replace
                origtext = xDialog.getChild("origtext")
                newtext = xDialog.getChild("newtext")
                new_button = xDialog.getChild("new")
                delete_button = xDialog.getChild("delete")
                replacements = xDialog.getChild("tabview")
                first_row = replacements.getChild("0")

                # A row selected before a query stops matching must be deselected, must disable
                # Delete, and cannot be selected again through the UI object.
                first_row.executeAction("SELECT", tuple())
                self.assertEqual("1", get_state_as_dict(replacements)["SelectionCount"])
                self.assertEqual("true", get_state_as_dict(delete_button)["Enabled"])
                no_match = "__autocorrect_filter_no_match_7d6f7c__"
                self.replace_text(search, no_match)
                self.ui_test.wait_until_property_is_updated(
                    first_row, "IsSemiTransparent", "true")
                self.assertEqual("0", get_state_as_dict(replacements)["SelectionCount"])
                self.assertEqual("false", get_state_as_dict(delete_button)["Enabled"])
                first_row.executeAction("SELECT", tuple())
                self.assertEqual("0", get_state_as_dict(replacements)["SelectionCount"])

                # A newly inserted nonmatch starts life sensitive; the mutation path must
                # immediately reapply the active query and make it non-actionable.
                inserted_short = "__autocorrect_inserted_nonmatch_7d6f7c__"
                self.replace_text(origtext, inserted_short)
                self.replace_text(newtext, "__autocorrect_inserted_value__")
                new_button.executeAction("CLICK", tuple())
                inserted_row = self.find_tree_row(replacements, inserted_short)
                self.assertIsNotNone(inserted_row)
                self.assertEqual(
                    "true", get_state_as_dict(inserted_row)["IsSemiTransparent"])
                inserted_row.executeAction("SELECT", tuple())
                self.assertEqual("0", get_state_as_dict(replacements)["SelectionCount"])

                # Replacing a currently matching rule can make it stop matching. The replacement
                # path must reapply the query just like a fresh insertion.
                replace_match = "__autocorrect_replace_match_7d6f7c__"
                replace_short = "__autocorrect_replace_short_7d6f7c__"
                self.replace_text(search, replace_match)
                self.replace_text(origtext, replace_short)
                self.replace_text(newtext, replace_match)
                new_button.executeAction("CLICK", tuple())
                replace_row = self.find_tree_row(replacements, replace_short)
                self.assertIsNotNone(replace_row)
                self.assertEqual(
                    "false", get_state_as_dict(replace_row)["IsSemiTransparent"])
                self.replace_text(newtext, "__autocorrect_replaced_nonmatch__")
                new_button.executeAction("CLICK", tuple())
                replace_row = self.find_tree_row(replacements, replace_short)
                self.assertIsNotNone(replace_row)
                self.assertEqual(
                    "true", get_state_as_dict(replace_row)["IsSemiTransparent"])
                self.assertEqual("0", get_state_as_dict(replacements)["SelectionCount"])
                self.assertEqual("false", get_state_as_dict(delete_button)["Enabled"])

                # Delete follows the same successful-mutation refresh path.
                self.replace_text(search, replace_short)
                replace_row = self.find_tree_row(replacements, replace_short)
                self.ui_test.wait_until_property_is_updated(
                    replace_row, "IsSemiTransparent", "false")
                self.assertEqual("true", get_state_as_dict(delete_button)["Enabled"])
                delete_button.executeAction("CLICK", tuple())
                self.assertIsNone(self.find_tree_row(replacements, replace_short))

                # Switching language reconstructs the Replace list; the query must still govern
                # every reconstructed row.
                self.replace_text(search, no_match)
                nonempty = self.select_nonempty_language(language, (replacements,))
                self.assertIsNotNone(nonempty)
                language_row = nonempty.getChild("0")
                self.assertEqual(
                    "true", get_state_as_dict(language_row)["IsSemiTransparent"])
                language_row.executeAction("SELECT", tuple())
                self.assertEqual("0", get_state_as_dict(nonempty)["SelectionCount"])

                select_pos(tabs, "1")  # Exceptions
                abbrev = xDialog.getChild("abbrev")
                new_abbrev = xDialog.getChild("newabbrev")
                delete_abbrev = xDialog.getChild("delabbrev")
                abbreviations = xDialog.getChild("abbrevlist")
                double = xDialog.getChild("double")
                new_double = xDialog.getChild("newdouble")
                delete_double = xDialog.getChild("deldouble")
                double_caps = xDialog.getChild("doublelist")

                # Exception insertions are sorted after append; regardless of their final row,
                # the active query must immediately make a nonmatch insensitive.
                exception_text = "__autocorrect_exception_nonmatch_7d6f7c__"
                self.replace_text(abbrev, exception_text)
                new_abbrev.executeAction("CLICK", tuple())
                exception_row = self.find_tree_row(abbreviations, exception_text)
                self.assertIsNotNone(exception_row)
                self.assertEqual(
                    "true", get_state_as_dict(exception_row)["IsSemiTransparent"])
                exception_row.executeAction("SELECT", tuple())
                self.assertEqual("0", get_state_as_dict(abbreviations)["SelectionCount"])
                self.assertEqual("false", get_state_as_dict(delete_abbrev)["Enabled"])

                self.replace_text(search, exception_text)
                exception_row = self.find_tree_row(abbreviations, exception_text)
                self.ui_test.wait_until_property_is_updated(
                    exception_row, "IsSemiTransparent", "false")
                self.assertEqual("true", get_state_as_dict(delete_abbrev)["Enabled"])
                delete_abbrev.executeAction("CLICK", tuple())
                self.assertIsNone(self.find_tree_row(abbreviations, exception_text))

                # The second exception list has a separate mutation branch and must honor the
                # active query too.
                self.replace_text(search, no_match)
                double_text = "__autocorrect_double_nonmatch_7d6f7c__"
                self.replace_text(double, double_text)
                new_double.executeAction("CLICK", tuple())
                double_row = self.find_tree_row(double_caps, double_text)
                self.assertIsNotNone(double_row)
                self.assertEqual(
                    "true", get_state_as_dict(double_row)["IsSemiTransparent"])
                double_row.executeAction("SELECT", tuple())
                self.assertEqual("0", get_state_as_dict(double_caps)["SelectionCount"])
                self.assertEqual("false", get_state_as_dict(delete_double)["Enabled"])

                # The Exceptions page has its own language refill path and must preserve the same
                # row-sensitivity contract for either populated exception list.
                nonempty = self.select_nonempty_language(
                    language, (abbreviations, double_caps))
                self.assertIsNotNone(nonempty)
                language_row = nonempty.getChild("0")
                self.assertEqual(
                    "true", get_state_as_dict(language_row)["IsSemiTransparent"])
                language_row.executeAction("SELECT", tuple())
                self.assertEqual("0", get_state_as_dict(nonempty)["SelectionCount"])



# vim: set shiftwidth=4 softtabstop=4 expandtab:
