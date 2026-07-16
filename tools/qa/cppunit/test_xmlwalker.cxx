/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/*
 * This file is part of the LibreOffice project.
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include <algorithm>
#include <cppunit/extensions/HelperMacros.h>
#include <test/bootstrapfixture.hxx>
#include <rtl/ustring.hxx>
#include <tools/stream.hxx>
#include <tools/XmlWalker.hxx>

namespace
{
class XmlWalkerTest : public test::BootstrapFixture
{
    OUString maBasePath;

public:
    XmlWalkerTest()
        : BootstrapFixture(true, false)
    {
    }

    virtual void setUp() override { maBasePath = m_directories.getURLFromSrc(u"/tools/qa/data/"); }

    void testReadXML();

    CPPUNIT_TEST_SUITE(XmlWalkerTest);
    CPPUNIT_TEST(testReadXML);
    CPPUNIT_TEST_SUITE_END();
};

void XmlWalkerTest::testReadXML()
{
    OUString aXmlFilePath = maBasePath + "test.xml";

    tools::XmlWalker aWalker;
    SvFileStream aFileStream(aXmlFilePath, StreamMode::READ);
    CPPUNIT_ASSERT(aWalker.open(&aFileStream));
    CPPUNIT_ASSERT_EQUAL(std::string_view("root"), aWalker.name());
    CPPUNIT_ASSERT(aWalker.isElement());
    CPPUNIT_ASSERT(!aWalker.isBlank());
    CPPUNIT_ASSERT_EQUAL("Hello World"_ostr, aWalker.attribute("root-attr"_ostr));
    const auto aRootAttributes = aWalker.attributeNames();
    CPPUNIT_ASSERT_EQUAL(size_t(1), aRootAttributes.size());
    CPPUNIT_ASSERT_EQUAL("root-attr"_ostr, aRootAttributes[0]);

    int nNumberOfChildNodes = 0;
    bool bSawComment = false;

    aWalker.children();
    while (aWalker.isValid())
    {
        if (!aWalker.isElement())
        {
            CPPUNIT_ASSERT(aWalker.isBlank() || aWalker.isComment());
            bSawComment |= aWalker.isComment();
            aWalker.next();
            continue;
        }
        if (aWalker.name() == "child")
        {
            nNumberOfChildNodes++;

            CPPUNIT_ASSERT_EQUAL(OString(OString::number(nNumberOfChildNodes)),
                                 aWalker.attribute("number"_ostr));

            if (nNumberOfChildNodes == 1) // only the first node has the attribute
                CPPUNIT_ASSERT_EQUAL("123"_ostr, aWalker.attribute("attribute"_ostr));
            else
                CPPUNIT_ASSERT_EQUAL(OString(), aWalker.attribute("attribute"_ostr));

            aWalker.children();
            while (aWalker.isValid())
            {
                if (aWalker.name() == "grandchild")
                {
                    CPPUNIT_ASSERT(aWalker.isElement());
                    CPPUNIT_ASSERT_EQUAL("ABC"_ostr, aWalker.attribute("attribute1"_ostr));
                    CPPUNIT_ASSERT_EQUAL("CDE"_ostr, aWalker.attribute("attribute2"_ostr));
                    auto aAttributeNames = aWalker.attributeNames();
                    std::sort(aAttributeNames.begin(), aAttributeNames.end());
                    CPPUNIT_ASSERT_EQUAL(size_t(2), aAttributeNames.size());
                    CPPUNIT_ASSERT_EQUAL("attribute1"_ostr, aAttributeNames[0]);
                    CPPUNIT_ASSERT_EQUAL("attribute2"_ostr, aAttributeNames[1]);
                    CPPUNIT_ASSERT_EQUAL("Content"_ostr, aWalker.content());
                }
                aWalker.next();
            }
            aWalker.parent();
        }
        else if (aWalker.name() == "with-namespace")
        {
            CPPUNIT_ASSERT_EQUAL(std::string_view("adobe:ns:meta/"), aWalker.namespaceHref());
            CPPUNIT_ASSERT_EQUAL(std::string_view("xx"), aWalker.namespacePrefix());

            aWalker.children();
            while (aWalker.isValid())
            {
                if (aWalker.name() == "namespace-child")
                {
                    CPPUNIT_ASSERT_EQUAL(std::string_view("adobe:ns:meta/"),
                                         aWalker.namespaceHref());
                    CPPUNIT_ASSERT_EQUAL(std::string_view("xx"), aWalker.namespacePrefix());
                }
                aWalker.next();
            }
            aWalker.parent();
        }
        aWalker.next();
    }
    aWalker.parent();

    CPPUNIT_ASSERT_EQUAL(3, nNumberOfChildNodes);
    CPPUNIT_ASSERT(bSawComment);
}

CPPUNIT_TEST_SUITE_REGISTRATION(XmlWalkerTest);
}

/* vim:set shiftwidth=4 softtabstop=4 expandtab: */
