# -*- Mode: makefile-gmake; tab-width: 4; indent-tabs-mode: t -*-
#
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

$(eval $(call gb_CppunitTest_CppunitTest,vcl_file_definition_widget_draw_test))

$(call gb_CppunitTest_get_target,vcl_file_definition_widget_draw_test) : gb_TEST_ENV_VARS += SAL_USE_VCLPLUGIN=svp
$(call gb_CppunitTest_get_target,vcl_file_definition_widget_draw_test) : gb_TEST_ENV_VARS += VCL_DRAW_WIDGETS_FROM_FILE=1
$(call gb_CppunitTest_get_target,vcl_file_definition_widget_draw_test) : gb_TEST_ENV_VARS += VCL_FILE_WIDGET_THEME=material

$(eval $(call gb_CppunitTest_add_exception_objects,vcl_file_definition_widget_draw_test, \
    vcl/qa/cppunit/widgetdraw/FileDefinitionWidgetDrawTest \
))

$(eval $(call gb_CppunitTest_set_include,vcl_file_definition_widget_draw_test, \
    $$(INCLUDE) \
    -I$(SRCDIR)/vcl/inc \
))

$(eval $(call gb_CppunitTest_use_externals,vcl_file_definition_widget_draw_test, \
    boost_headers \
    harfbuzz \
))

$(eval $(call gb_CppunitTest_use_libraries,vcl_file_definition_widget_draw_test, \
    basegfx \
    comphelper \
    cppu \
    cppuhelper \
    sal \
    svt \
    test \
    tl \
    unotest \
    vcl \
))

$(eval $(call gb_CppunitTest_use_sdk_api,vcl_file_definition_widget_draw_test))

$(eval $(call gb_CppunitTest_use_ure,vcl_file_definition_widget_draw_test))
$(eval $(call gb_CppunitTest_use_vcl,vcl_file_definition_widget_draw_test))

$(eval $(call gb_CppunitTest_use_components,vcl_file_definition_widget_draw_test, \
    configmgr/source/configmgr \
    i18npool/util/i18npool \
    ucb/source/core/ucb1 \
    unotools/util/utl \
))

$(eval $(call gb_CppunitTest_use_packages,vcl_file_definition_widget_draw_test, \
    vcl_theme_definitions \
))

$(eval $(call gb_CppunitTest_use_configuration,vcl_file_definition_widget_draw_test))

# vim: set noet sw=4 ts=4:
