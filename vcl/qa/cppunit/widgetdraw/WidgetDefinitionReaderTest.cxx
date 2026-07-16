/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <sal/config.h>

#include <string_view>

#include <cppunit/TestAssert.h>
#include <cppunit/extensions/HelperMacros.h>
#include <cppunit/plugin/TestPlugIn.h>
#include <unotest/bootstrapfixturebase.hxx>

#include <widgetdraw/WidgetDefinitionReader.hxx>

namespace
{
constexpr OUStringLiteral gaDataUrl(u"/vcl/qa/cppunit/widgetdraw/data/");
constexpr OUStringLiteral gaMaterialThemeUrl(u"/vcl/uiconfig/theme_definitions/material/");

class WidgetDefinitionReaderTest : public test::BootstrapFixtureBase
{
private:
    OUString getFullUrl(std::u16string_view sFileName)
    {
        return m_directories.getURLFromSrc(gaDataUrl) + sFileName;
    }

    OUString getMaterialThemeUrl(std::u16string_view sFileName)
    {
        return m_directories.getURLFromSrc(gaMaterialThemeUrl) + sFileName;
    }

public:
    void testRead();
    void testReadSettings();
    void testReadMaterialTheme();

    CPPUNIT_TEST_SUITE(WidgetDefinitionReaderTest);
    CPPUNIT_TEST(testRead);
    CPPUNIT_TEST(testReadSettings);
    CPPUNIT_TEST(testReadMaterialTheme);
    CPPUNIT_TEST_SUITE_END();
};

void WidgetDefinitionReaderTest::testReadMaterialTheme()
{
    vcl::WidgetDefinition aDefinition;
    vcl::WidgetDefinitionReader aReader(getMaterialThemeUrl(u"definition.xml"),
                                        getMaterialThemeUrl(u""));
    CPPUNIT_ASSERT(aReader.read(aDefinition));

    CPPUNIT_ASSERT_EQUAL(u"fffbfe"_ustr, aDefinition.mpStyle->maWindowColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"1d1b20"_ustr,
                         aDefinition.mpStyle->maWindowTextColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"e8def8"_ustr,
                         aDefinition.mpStyle->maHighlightColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"ffffff"_ustr,
                         aDefinition.mpStyle->maActionButtonTextColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"f4eff4"_ustr,
                         aDefinition.mpStyle->maHelpTextColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL("12"_ostr, aDefinition.mpSettings->msListBoxEntryMargin);

    auto pPushButton = aDefinition.getDefinition(ControlType::Pushbutton, ControlPart::Entire);
    CPPUNIT_ASSERT(pPushButton);
    const auto aPushButtonStates
        = pPushButton->getStates(ControlType::Pushbutton, ControlPart::Entire,
                                 ControlState::ENABLED, PushButtonValue());
    CPPUNIT_ASSERT_EQUAL(size_t(1), aPushButtonStates.size());
    CPPUNIT_ASSERT_EQUAL(size_t(1), aPushButtonStates[0]->mpWidgetDrawActions.size());
    const auto& rButtonRect = static_cast<const vcl::WidgetDrawActionRectangle&>(
        *aPushButtonStates[0]->mpWidgetDrawActions[0]);
    CPPUNIT_ASSERT_EQUAL(sal_Int32(20), rButtonRect.mnRx);
    CPPUNIT_ASSERT_EQUAL(u"e8def8"_ustr, rButtonRect.maFillColor.AsRGBHexString());

    PushButtonValue aActionButtonValue;
    aActionButtonValue.mbIsAction = true;
    const auto aActionButtonStates
        = pPushButton->getStates(ControlType::Pushbutton, ControlPart::Entire,
                                 ControlState::ENABLED, aActionButtonValue);
    CPPUNIT_ASSERT_EQUAL(size_t(2), aActionButtonStates.size());
    const auto& rActionButtonRect = static_cast<const vcl::WidgetDrawActionRectangle&>(
        *aActionButtonStates.back()->mpWidgetDrawActions[0]);
    CPPUNIT_ASSERT_EQUAL(u"6750a4"_ustr, rActionButtonRect.maFillColor.AsRGBHexString());

    auto pPushButtonFocus
        = aDefinition.getDefinition(ControlType::Pushbutton, ControlPart::Focus);
    CPPUNIT_ASSERT(pPushButtonFocus);
    const auto aPushButtonFocusStates
        = pPushButtonFocus->getStates(ControlType::Pushbutton, ControlPart::Focus,
                                      ControlState::FOCUSED, PushButtonValue());
    CPPUNIT_ASSERT_EQUAL(size_t(1), aPushButtonFocusStates.size());
    CPPUNIT_ASSERT_EQUAL(size_t(4),
                         aPushButtonFocusStates[0]->mpWidgetDrawActions.size());
    for (const auto& pAction : aPushButtonFocusStates[0]->mpWidgetDrawActions)
        CPPUNIT_ASSERT(pAction->maType == vcl::WidgetDrawActionType::LINE);

    auto pCheckbox = aDefinition.getDefinition(ControlType::Checkbox, ControlPart::Entire);
    CPPUNIT_ASSERT(pCheckbox);
    const auto aCheckedStates
        = pCheckbox->getStates(ControlType::Checkbox, ControlPart::Entire, ControlState::ENABLED,
                               ImplControlValue(ButtonValue::On));
    CPPUNIT_ASSERT_EQUAL(size_t(1), aCheckedStates.size());
    CPPUNIT_ASSERT_EQUAL(size_t(3), aCheckedStates[0]->mpWidgetDrawActions.size());

    auto pRadio = aDefinition.getDefinition(ControlType::Radiobutton, ControlPart::Entire);
    CPPUNIT_ASSERT(pRadio);
    const auto aSelectedRadioStates
        = pRadio->getStates(ControlType::Radiobutton, ControlPart::Entire, ControlState::ENABLED,
                            ImplControlValue(ButtonValue::On));
    CPPUNIT_ASSERT_EQUAL(size_t(1), aSelectedRadioStates.size());
    CPPUNIT_ASSERT_EQUAL(size_t(2), aSelectedRadioStates[0]->mpWidgetDrawActions.size());
    const auto& rRadioDot = static_cast<const vcl::WidgetDrawActionRectangle&>(
        *aSelectedRadioStates[0]->mpWidgetDrawActions[1]);
    CPPUNIT_ASSERT_DOUBLES_EQUAL(0.33, rRadioDot.mfX1, 0.001);
    CPPUNIT_ASSERT_DOUBLES_EQUAL(0.67, rRadioDot.mfX2, 0.001);

    auto pComboButton
        = aDefinition.getDefinition(ControlType::Combobox, ControlPart::ButtonDown);
    CPPUNIT_ASSERT(pComboButton);
    const auto aComboButtonStates
        = pComboButton->getStates(ControlType::Combobox, ControlPart::ButtonDown,
                                  ControlState::ENABLED, ImplControlValue());
    CPPUNIT_ASSERT_EQUAL(size_t(1), aComboButtonStates.size());
    CPPUNIT_ASSERT_EQUAL(size_t(3), aComboButtonStates[0]->mpWidgetDrawActions.size());

    auto pTab = aDefinition.getDefinition(ControlType::TabItem, ControlPart::Entire);
    CPPUNIT_ASSERT(pTab);
    const TabitemValue aTabValue(tools::Rectangle(), TabBarPosition::Top);
    const auto aSelectedTabStates
        = pTab->getStates(ControlType::TabItem, ControlPart::Entire,
                          ControlState::ENABLED | ControlState::SELECTED, aTabValue);
    CPPUNIT_ASSERT_EQUAL(size_t(2), aSelectedTabStates.size());

    auto pListHeaderButton
        = aDefinition.getDefinition(ControlType::ListHeader, ControlPart::Button);
    CPPUNIT_ASSERT(pListHeaderButton);
    auto pListHeaderArrow
        = aDefinition.getDefinition(ControlType::ListHeader, ControlPart::Arrow);
    CPPUNIT_ASSERT(pListHeaderArrow);
    const auto aDownArrowStates
        = pListHeaderArrow->getStates(ControlType::ListHeader, ControlPart::Arrow,
                                      ControlState::ENABLED, ImplControlValue(tools::Long(1)));
    CPPUNIT_ASSERT_EQUAL(size_t(1), aDownArrowStates.size());
    CPPUNIT_ASSERT_EQUAL(size_t(2), aDownArrowStates[0]->mpWidgetDrawActions.size());
}

void WidgetDefinitionReaderTest::testReadSettings()
{
    {
        vcl::WidgetDefinition aDefinition;
        vcl::WidgetDefinitionReader aReader(getFullUrl(u"definitionSettings1.xml"),
                                            getFullUrl(u""));
        CPPUNIT_ASSERT(aReader.read(aDefinition));
        CPPUNIT_ASSERT_EQUAL(""_ostr, aDefinition.mpSettings->msCenteredTabs);
    }

    {
        vcl::WidgetDefinition aDefinition;
        vcl::WidgetDefinitionReader aReader(getFullUrl(u"definitionSettings2.xml"),
                                            getFullUrl(u""));
        CPPUNIT_ASSERT(aReader.read(aDefinition));
        CPPUNIT_ASSERT_EQUAL("true"_ostr, aDefinition.mpSettings->msCenteredTabs);
    }

    {
        vcl::WidgetDefinition aDefinition;
        vcl::WidgetDefinitionReader aReader(getFullUrl(u"definitionSettings3.xml"),
                                            getFullUrl(u""));
        CPPUNIT_ASSERT(aReader.read(aDefinition));
        CPPUNIT_ASSERT_EQUAL("true"_ostr, aDefinition.mpSettings->msNoActiveTabTextRaise);
        CPPUNIT_ASSERT_EQUAL("false"_ostr, aDefinition.mpSettings->msCenteredTabs);
        CPPUNIT_ASSERT_EQUAL("0"_ostr, aDefinition.mpSettings->msListBoxEntryMargin);
        CPPUNIT_ASSERT_EQUAL("10"_ostr, aDefinition.mpSettings->msDefaultFontSize);
        CPPUNIT_ASSERT_EQUAL("16"_ostr, aDefinition.mpSettings->msTitleHeight);
        CPPUNIT_ASSERT_EQUAL("12"_ostr, aDefinition.mpSettings->msFloatTitleHeight);
        CPPUNIT_ASSERT_EQUAL("15"_ostr, aDefinition.mpSettings->msListBoxPreviewDefaultLogicWidth);
        CPPUNIT_ASSERT_EQUAL("7"_ostr, aDefinition.mpSettings->msListBoxPreviewDefaultLogicHeight);
    }
}

void WidgetDefinitionReaderTest::testRead()
{
    vcl::WidgetDefinition aDefinition;

    vcl::WidgetDefinitionReader aReader(getFullUrl(u"definition1.xml"), getFullUrl(u""));
    CPPUNIT_ASSERT(aReader.read(aDefinition));

    CPPUNIT_ASSERT_EQUAL(u"123456"_ustr, aDefinition.mpStyle->maFaceColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"234567"_ustr, aDefinition.mpStyle->maCheckedColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"345678"_ustr, aDefinition.mpStyle->maLightColor.AsRGBHexString());

    CPPUNIT_ASSERT_EQUAL(u"ffffff"_ustr, aDefinition.mpStyle->maVisitedLinkColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"ffffff"_ustr, aDefinition.mpStyle->maToolTextColor.AsRGBHexString());
    CPPUNIT_ASSERT_EQUAL(u"ffffff"_ustr, aDefinition.mpStyle->maWindowTextColor.AsRGBHexString());

    // Pushbutton
    {
        ControlState eState
            = ControlState::DEFAULT | ControlState::ENABLED | ControlState::ROLLOVER;
        std::vector<std::shared_ptr<vcl::WidgetDefinitionState>> aStates
            = aDefinition.getDefinition(ControlType::Pushbutton, ControlPart::Entire)
                  ->getStates(ControlType::Pushbutton, ControlPart::Entire, eState,
                              PushButtonValue());

        CPPUNIT_ASSERT_EQUAL(size_t(2), aStates.size());

        CPPUNIT_ASSERT_EQUAL(size_t(2), aStates[0]->mpWidgetDrawActions.size());
        CPPUNIT_ASSERT_EQUAL(vcl::WidgetDrawActionType::RECTANGLE,
                             aStates[0]->mpWidgetDrawActions[0]->maType);
        CPPUNIT_ASSERT_EQUAL(vcl::WidgetDrawActionType::LINE,
                             aStates[0]->mpWidgetDrawActions[1]->maType);
    }

    // Radiobutton
    {
        std::vector<std::shared_ptr<vcl::WidgetDefinitionState>> aStates
            = aDefinition.getDefinition(ControlType::Radiobutton, ControlPart::Entire)
                  ->getStates(ControlType::Radiobutton, ControlPart::Entire, ControlState::NONE,
                              ImplControlValue(ButtonValue::On));
        CPPUNIT_ASSERT_EQUAL(size_t(1), aStates.size());
        CPPUNIT_ASSERT_EQUAL(size_t(2), aStates[0]->mpWidgetDrawActions.size());
    }

    {
        std::vector<std::shared_ptr<vcl::WidgetDefinitionState>> aStates
            = aDefinition.getDefinition(ControlType::Radiobutton, ControlPart::Entire)
                  ->getStates(ControlType::Radiobutton, ControlPart::Entire, ControlState::NONE,
                              ImplControlValue(ButtonValue::Off));
        CPPUNIT_ASSERT_EQUAL(size_t(1), aStates.size());
        CPPUNIT_ASSERT_EQUAL(size_t(1), aStates[0]->mpWidgetDrawActions.size());
    }
}

} // namespace

CPPUNIT_TEST_SUITE_REGISTRATION(WidgetDefinitionReaderTest);

CPPUNIT_PLUGIN_IMPLEMENT();

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
