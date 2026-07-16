/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <sal/config.h>

#include <cppunit/TestAssert.h>
#include <cppunit/extensions/HelperMacros.h>
#include <cppunit/plugin/TestPlugIn.h>
#include <test/bootstrapfixture.hxx>

#include <tools/color.hxx>
#include <tools/gen.hxx>
#include <vcl/salnativewidgets.hxx>
#include <vcl/virdev.hxx>
#include <vcl/wall.hxx>

#include <toolbarvalue.hxx>

namespace
{
constexpr tools::Long gnDeviceWidth = 160;
constexpr tools::Long gnDeviceHeight = 96;

void initializeDevice(VirtualDevice& rDevice)
{
    CPPUNIT_ASSERT(rDevice.SetOutputSizePixel(Size(gnDeviceWidth, gnDeviceHeight)));
    rDevice.SetBackground(Wallpaper(COL_WHITE));
    rDevice.Erase();
}

class FileDefinitionWidgetDrawTest : public test::BootstrapFixture
{
public:
    FileDefinitionWidgetDrawTest()
        : BootstrapFixture(true, false)
    {
    }
};

CPPUNIT_TEST_FIXTURE(FileDefinitionWidgetDrawTest, testComboBoxLtrAndRtlGeometryAndPixels)
{
    constexpr tools::Long nControlX = 20;
    constexpr tools::Long nControlY = 10;
    constexpr tools::Long nControlWidth = 120;
    constexpr tools::Long nControlHeight = 40;
    constexpr tools::Long nButtonWidth = 36;
    constexpr tools::Long nButtonHeight = 36;

    const tools::Rectangle aControlRegion(Point(nControlX, nControlY),
                                          Size(nControlWidth, nControlHeight));
    const tools::Rectangle aExpectedButton(Point(nControlX + nControlWidth - nButtonWidth,
                                                 nControlY + (nControlHeight - nButtonHeight) / 2),
                                           Size(nButtonWidth, nButtonHeight));
    const tools::Rectangle aExpectedSubEdit(
        Point(nControlX + 1, nControlY + 1),
        Size(nControlWidth - nButtonWidth - 1, nControlHeight - 2));
    const ImplControlValue aValue;

    ScopedVclPtrInstance<VirtualDevice> xLtrDevice;
    initializeDevice(*xLtrDevice);

    CPPUNIT_ASSERT(
        xLtrDevice->IsNativeControlSupported(ControlType::Combobox, ControlPart::Entire));
    CPPUNIT_ASSERT(
        xLtrDevice->IsNativeControlSupported(ControlType::Combobox, ControlPart::ButtonDown));

    tools::Rectangle aBoundingRegion;
    tools::Rectangle aContentRegion;
    CPPUNIT_ASSERT(xLtrDevice->GetNativeControlRegion(
        ControlType::Combobox, ControlPart::ButtonDown, aControlRegion, ControlState::ENABLED,
        aValue, aBoundingRegion, aContentRegion));
    CPPUNIT_ASSERT_EQUAL(aExpectedButton, aBoundingRegion);
    CPPUNIT_ASSERT_EQUAL(aExpectedButton, aContentRegion);

    CPPUNIT_ASSERT(xLtrDevice->GetNativeControlRegion(ControlType::Combobox, ControlPart::SubEdit,
                                                      aControlRegion, ControlState::ENABLED, aValue,
                                                      aBoundingRegion, aContentRegion));
    CPPUNIT_ASSERT_EQUAL(aExpectedSubEdit, aBoundingRegion);
    CPPUNIT_ASSERT_EQUAL(aExpectedSubEdit, aContentRegion);

    CPPUNIT_ASSERT(xLtrDevice->DrawNativeControl(ControlType::Combobox, ControlPart::Entire,
                                                 aControlRegion, ControlState::ENABLED, aValue,
                                                 OUString()));

    const Color aLtrButtonColor
        = xLtrDevice->GetPixel(Point(aExpectedButton.Left() + 8, aExpectedButton.Center().Y()));
    const Color aLtrSurfaceColor
        = xLtrDevice->GetPixel(Point(nControlX + 8, aExpectedButton.Center().Y()));
    CPPUNIT_ASSERT(aLtrButtonColor != aLtrSurfaceColor);

    ScopedVclPtrInstance<VirtualDevice> xRtlDevice;
    initializeDevice(*xRtlDevice);
    xRtlDevice->EnableRTL();

    CPPUNIT_ASSERT(xRtlDevice->GetNativeControlRegion(
        ControlType::Combobox, ControlPart::ButtonDown, aControlRegion, ControlState::ENABLED,
        aValue, aBoundingRegion, aContentRegion));
    // Native regions are converted back to logical coordinates for callers.
    CPPUNIT_ASSERT_EQUAL(aExpectedButton, aBoundingRegion);
    CPPUNIT_ASSERT_EQUAL(aExpectedButton, aContentRegion);

    CPPUNIT_ASSERT(xRtlDevice->GetNativeControlRegion(ControlType::Combobox, ControlPart::SubEdit,
                                                      aControlRegion, ControlState::ENABLED, aValue,
                                                      aBoundingRegion, aContentRegion));
    CPPUNIT_ASSERT_EQUAL(aExpectedSubEdit, aBoundingRegion);
    CPPUNIT_ASSERT_EQUAL(aExpectedSubEdit, aContentRegion);

    CPPUNIT_ASSERT(xRtlDevice->DrawNativeControl(ControlType::Combobox, ControlPart::Entire,
                                                 aControlRegion, ControlState::ENABLED, aValue,
                                                 OUString()));

    // The control is centered horizontally, so mirroring keeps its outer bounds
    // fixed. Disable logical mirroring only for raw physical-pixel inspection.
    xRtlDevice->EnableRTL(false);
    const Point aRtlButtonSample(nControlX + 8, aExpectedButton.Center().Y());
    const Point aRtlSurfaceSample(aExpectedButton.Left() + 8, aExpectedButton.Center().Y());
    const Color aRtlButtonColor = xRtlDevice->GetPixel(aRtlButtonSample);
    const Color aRtlSurfaceColor = xRtlDevice->GetPixel(aRtlSurfaceSample);

    CPPUNIT_ASSERT_EQUAL(aLtrButtonColor, aRtlButtonColor);
    CPPUNIT_ASSERT_EQUAL(aLtrSurfaceColor, aRtlSurfaceColor);
    CPPUNIT_ASSERT(aRtlButtonColor != aRtlSurfaceColor);
}

CPPUNIT_TEST_FIXTURE(FileDefinitionWidgetDrawTest, testToolbarGripUsesValueGeometry)
{
    ScopedVclPtrInstance<VirtualDevice> xDevice;
    initializeDevice(*xDevice);

    CPPUNIT_ASSERT(xDevice->IsNativeControlSupported(ControlType::Toolbar, ControlPart::ThumbVert));

    const tools::Rectangle aControlRegion(Point(10, 8), Size(100, 60));
    ToolbarValue aValue;
    aValue.maGripRect = tools::Rectangle(Point(31, 17), Size(12, 36));

    CPPUNIT_ASSERT(xDevice->DrawNativeControl(ControlType::Toolbar, ControlPart::ThumbVert,
                                              aControlRegion, ControlState::ENABLED, aValue,
                                              OUString()));

    CPPUNIT_ASSERT_EQUAL(COL_WHITE, xDevice->GetPixel(Point(20, 30)));
    CPPUNIT_ASSERT(xDevice->GetPixel(aValue.maGripRect.Center()) != COL_WHITE);
}

CPPUNIT_TEST_FIXTURE(FileDefinitionWidgetDrawTest, testStandaloneSpinButtonComposites)
{
    ScopedVclPtrInstance<VirtualDevice> xVerticalDevice;
    initializeDevice(*xVerticalDevice);

    CPPUNIT_ASSERT(
        xVerticalDevice->IsNativeControlSupported(ControlType::SpinButtons, ControlPart::Entire));
    CPPUNIT_ASSERT(xVerticalDevice->IsNativeControlSupported(ControlType::SpinButtons,
                                                             ControlPart::AllButtons));

    SpinbuttonValue aVerticalValue;
    aVerticalValue.maUpperRect = tools::Rectangle(Point(12, 8), Size(40, 40));
    aVerticalValue.maLowerRect = tools::Rectangle(Point(12, 52), Size(40, 40));
    aVerticalValue.mnUpperPart = ControlPart::ButtonUp;
    aVerticalValue.mnLowerPart = ControlPart::ButtonDown;
    aVerticalValue.mnUpperState = ControlState::ENABLED | ControlState::ROLLOVER;
    aVerticalValue.mnLowerState = ControlState::ENABLED | ControlState::PRESSED;

    CPPUNIT_ASSERT(xVerticalDevice->DrawNativeControl(
        ControlType::SpinButtons, ControlPart::Entire, tools::Rectangle(Point(8, 4), Size(52, 90)),
        ControlState::ENABLED, aVerticalValue, OUString()));

    const Color aUpApex = xVerticalDevice->GetPixel(
        Point(aVerticalValue.maUpperRect.Left() + 20, aVerticalValue.maUpperRect.Top() + 16));
    const Color aUpOpposite = xVerticalDevice->GetPixel(
        Point(aVerticalValue.maUpperRect.Left() + 20, aVerticalValue.maUpperRect.Top() + 23));
    const Color aDownApex = xVerticalDevice->GetPixel(
        Point(aVerticalValue.maLowerRect.Left() + 20, aVerticalValue.maLowerRect.Top() + 23));
    const Color aDownOpposite = xVerticalDevice->GetPixel(
        Point(aVerticalValue.maLowerRect.Left() + 20, aVerticalValue.maLowerRect.Top() + 16));
    CPPUNIT_ASSERT(aUpApex != aUpOpposite);
    CPPUNIT_ASSERT(aDownApex != aDownOpposite);

    const Color aRolloverFill = xVerticalDevice->GetPixel(
        Point(aVerticalValue.maUpperRect.Left() + 5, aVerticalValue.maUpperRect.Center().Y()));
    const Color aPressedFill = xVerticalDevice->GetPixel(
        Point(aVerticalValue.maLowerRect.Left() + 5, aVerticalValue.maLowerRect.Center().Y()));
    CPPUNIT_ASSERT(aRolloverFill != COL_WHITE);
    CPPUNIT_ASSERT(aPressedFill != COL_WHITE);
    CPPUNIT_ASSERT(aRolloverFill != aPressedFill);
    CPPUNIT_ASSERT_EQUAL(COL_WHITE, xVerticalDevice->GetPixel(Point(70, 30)));

    ScopedVclPtrInstance<VirtualDevice> xHorizontalDevice;
    initializeDevice(*xHorizontalDevice);

    SpinbuttonValue aHorizontalValue;
    aHorizontalValue.maUpperRect = tools::Rectangle(Point(68, 20), Size(40, 40));
    aHorizontalValue.maLowerRect = tools::Rectangle(Point(112, 20), Size(40, 40));
    aHorizontalValue.mnUpperPart = ControlPart::ButtonRight;
    aHorizontalValue.mnLowerPart = ControlPart::ButtonLeft;
    aHorizontalValue.mnUpperState = ControlState::ENABLED | ControlState::ROLLOVER;
    aHorizontalValue.mnLowerState = ControlState::ENABLED | ControlState::PRESSED;

    CPPUNIT_ASSERT(
        xHorizontalDevice->DrawNativeControl(ControlType::SpinButtons, ControlPart::AllButtons,
                                             tools::Rectangle(Point(64, 16), Size(92, 48)),
                                             ControlState::ENABLED, aHorizontalValue, OUString()));

    const Color aRightApex = xHorizontalDevice->GetPixel(
        Point(aHorizontalValue.maUpperRect.Left() + 23, aHorizontalValue.maUpperRect.Top() + 20));
    const Color aRightOpposite = xHorizontalDevice->GetPixel(
        Point(aHorizontalValue.maUpperRect.Left() + 16, aHorizontalValue.maUpperRect.Top() + 20));
    const Color aLeftApex = xHorizontalDevice->GetPixel(
        Point(aHorizontalValue.maLowerRect.Left() + 16, aHorizontalValue.maLowerRect.Top() + 20));
    const Color aLeftOpposite = xHorizontalDevice->GetPixel(
        Point(aHorizontalValue.maLowerRect.Left() + 23, aHorizontalValue.maLowerRect.Top() + 20));
    CPPUNIT_ASSERT(aRightApex != aRightOpposite);
    CPPUNIT_ASSERT(aLeftApex != aLeftOpposite);

    CPPUNIT_ASSERT_EQUAL(aRolloverFill, xHorizontalDevice->GetPixel(
                                            Point(aHorizontalValue.maUpperRect.Left() + 5,
                                                  aHorizontalValue.maUpperRect.Center().Y())));
    CPPUNIT_ASSERT_EQUAL(aPressedFill, xHorizontalDevice->GetPixel(
                                           Point(aHorizontalValue.maLowerRect.Left() + 5,
                                                 aHorizontalValue.maLowerRect.Center().Y())));
    CPPUNIT_ASSERT_EQUAL(COL_WHITE, xHorizontalDevice->GetPixel(Point(20, 30)));
}

CPPUNIT_TEST_FIXTURE(FileDefinitionWidgetDrawTest, testNativeDrawingInvalidatesColorCache)
{
    ScopedVclPtrInstance<VirtualDevice> xDevice;
    initializeDevice(*xDevice);

    xDevice->SetLineColor(COL_BLUE);
    xDevice->SetFillColor(COL_RED);

    const tools::Rectangle aComboRegion(Point(20, 8), Size(120, 40));
    CPPUNIT_ASSERT(xDevice->DrawNativeControl(ControlType::Combobox, ControlPart::Entire,
                                              aComboRegion, ControlState::ENABLED,
                                              ImplControlValue(), OUString()));

    const tools::Rectangle aOrdinaryRectangle(Point(12, 62), Size(28, 22));
    xDevice->DrawRect(aOrdinaryRectangle);

    CPPUNIT_ASSERT_EQUAL(COL_RED, xDevice->GetPixel(aOrdinaryRectangle.Center()));
    CPPUNIT_ASSERT_EQUAL(COL_BLUE, xDevice->GetPixel(Point(aOrdinaryRectangle.Center().X(),
                                                           aOrdinaryRectangle.Top())));
}

} // namespace

CPPUNIT_PLUGIN_IMPLEMENT();

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
