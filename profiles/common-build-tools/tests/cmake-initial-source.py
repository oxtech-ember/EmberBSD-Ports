#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Source guards for unavailable optional Darwin operations. Executes no tool."""
import argparse
from pathlib import Path
import re
import unittest

CMAKE = None
LLVM = None


def function(source, name):
    begin = source.index(name)
    match = re.search(r'\n(?:void|bool) cm[A-Za-z0-9_:]+\(', source[begin+len(name):])
    return source[begin:begin+len(name)+match.start()] if match else source[begin:]


class InitialSourceTests(unittest.TestCase):
    def test_initial_policy_has_finite_native_darwin_boundary(self):
        path = CMAKE / 'Modules/Platform/EmberBSD-DarwinTools.cmake'
        self.assertTrue(path.is_file(), 'Missing explicit optional-operation policy')
        text = path.read_text()
        for word in ('EMBERBSD_CMAKE_NATIVE_TOOLS', 'CMAKE_HOST_APPLE', 'Darwin', 'initial', 'full', 'FATAL_ERROR'):
            self.assertIn(word, text)

    def test_provided_initial_cache_paths_are_real_executables_not_placeholders(self):
        text = (CMAKE / 'Modules/Platform/EmberBSD-DarwinTools.cmake').read_text()
        for word in ('CMAKE_INSTALL_NAME_TOOL', 'CMAKE_TAPI', 'IS_ABSOLUTE',
                     'IS_DIRECTORY', 'IS_EXECUTABLE', 'DEFINED'):
            self.assertIn(word, text)

    def test_findbinutils_never_discovers_unavailable_initial_tools(self):
        text = (CMAKE / 'Modules/CMakeFindBinUtils.cmake').read_text()
        self.assertIn('include(Platform/EmberBSD-DarwinTools)', text)
        self.assertIn('list(REMOVE_ITEM _CMAKE_TOOL_VARS TAPI)', text)
        self.assertIn('NOT _EMBERBSD_DARWIN_INITIAL_TOOLS AND APPLE', text)
        self.assertIn('CMAKE_PLATFORM_HAS_INSTALLNAME AND NOT _EMBERBSD_DARWIN_INITIAL_TOOLS', text)

    def test_platform_does_not_find_an_unavailable_install_name_tool(self):
        text = (CMAKE / 'Modules/Platform/Darwin.cmake').read_text()
        self.assertIn('NOT _EMBERBSD_DARWIN_INITIAL_TOOLS AND NOT DEFINED CMAKE_INSTALL_NAME_TOOL', text)
        self.assertIn('set(CMAKE_PLATFORM_HAS_INSTALLNAME 1)', text)

    def test_install_name_guard_is_after_required_remaps_are_known(self):
        text = function((CMAKE / 'Source/cmInstallTargetGenerator.cxx').read_text(),
                        'void cmInstallTargetGenerator::AddInstallNamePatchRule')
        early = text.index('installNameTool.empty()')
        self.assertGreater(early, text.index('std::string new_id'))
        self.assertIn('!new_id.empty() || !install_name_remap.empty()', text[:early])
        self.assertIn('MessageType::FATAL_ERROR', text[early:])
        self.assertIn('requires CMAKE_INSTALL_NAME_TOOL', text[early:])

    def test_actual_rpath_delta_without_tool_refuses_before_command_emission(self):
        text = function((CMAKE / 'Source/cmInstallTargetGenerator.cxx').read_text(),
                        'void cmInstallTargetGenerator::AddChrpathPatchRule')
        edit = text.index('if (!ordered.empty())')
        tail = text[edit:]
        self.assertIn('installNameTool.empty()', tail)
        self.assertLess(tail.index('MessageType::FATAL_ERROR'), tail.index('execute_process(COMMAND'))

    def test_shared_exports_cannot_disappear_when_tapi_is_unavailable(self):
        text = function((CMAKE / 'Source/cmGeneratorTarget.cxx').read_text(),
                        'bool cmGeneratorTarget::HasImportLibrary')
        self.assertIn('requires CMAKE_TAPI', text)
        guard = text.index('requires CMAKE_TAPI')
        self.assertLess(guard, text.index('PlatformSupportsAppleTextStubs'))
        for word in ('EMBERBSD_CMAKE_NATIVE_TOOLS', 'EMBERBSD_DARWIN_TOOL_PHASE',
                     'IsSharedLibraryWithExports()', 'generate_Stubs', 'IsSet("CMAKE_TAPI")', 'MessageType::FATAL_ERROR'):
            self.assertIn(word, text[:guard])

    def test_phase_and_package_variables_reach_both_nested_signatures(self):
        text = (CMAKE / 'Modules/CMakeFindBinUtils.cmake').read_text()
        self.assertIn('list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES', text)
        self.assertIn('CMAKE_TRY_COMPILE_PLATFORM_VARIABLES\n', text)
        self.assertIn('EMBERBSD_DARWIN_TOOL_PHASE', text)
        self.assertIn('CMAKE_POLICY_DEFAULT_CMP0137', text)
        self.assertIn('CMAKE_TRY_COMPILE_NO_PLATFORM_VARIABLES', text)
        self.assertNotIn('set(CMAKE_TRY_COMPILE_PLATFORM_VARIABLES', text)

    def test_global_shared_exports_reach_the_same_target_property(self):
        text = (CMAKE / 'Source/cmTarget.cxx').read_text()
        for word in ('CMAKE_SHARED_LIBRARY_ENABLE_EXPORTS', 'CMAKE_EXECUTABLE_ENABLE_EXPORTS',
                     'if (property == "ENABLE_EXPORTS"_s)', 'this->GetPropertyAsBool("ENABLE_EXPORTS")'):
            self.assertIn(word, text)
        text = (Path(__file__).with_name('cmake-initial') / 'CMakeLists.txt').read_text()
        for word in ('set(CMAKE_SHARED_LIBRARY_ENABLE_EXPORTS ON)',
                     'set_property(TARGET example PROPERTY ENABLE_EXPORTS ON)',
                     'set(CMAKE_ENABLE_EXPORTS ON)', 'BUILD_WITH_INSTALL_RPATH OFF',
                     'BUILD_WITH_INSTALL_NAME_DIR OFF'):
            self.assertIn(word, text)

    def test_archive_ar_mode_exits_before_libtool_discovery(self):
        text = (LLVM / 'llvm/cmake/modules/UseLibtool.cmake').read_text()
        self.assertIn('LLVM_DARWIN_ARCHIVE_TOOL', text)
        self.assertIn('set(LLVM_DARWIN_ARCHIVE_TOOL "libtool" CACHE STRING', text)
        self.assertIn('STREQUAL "ar"', text)
        self.assertIn('FATAL_ERROR', text)
        self.assertLess(text.index('return()'), text.index('find_program(CMAKE_XCRUN'))
        self.assertIn('-static ${LIBTOOL_NO_WARNING_FLAG}', text)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--cmake-source', type=Path, required=True)
    cli.add_argument('--llvm-source', type=Path, required=True)
    args, remaining = cli.parse_known_args()
    CMAKE, LLVM = args.cmake_source, args.llvm_source
    unittest.main(argv=[__file__, *remaining])
