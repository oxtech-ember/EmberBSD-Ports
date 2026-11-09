#!/usr/bin/env python3
"""Check installed wx CMake STC dependency discovery without compiling wx.

Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
"""
from pathlib import Path
import argparse, subprocess
p=argparse.ArgumentParser()
p.add_argument('--cmake', required=True, type=Path)
p.add_argument('--template', required=True, type=Path)
p.add_argument('--work', required=True, type=Path)
p.add_argument('--case', choices=['static','mono-static','shared','mono-shared','disabled'], action='append')
a=p.parse_args()
# This is a config-consumer fixture, not a wx/compiler/library build. The real
# package config template is configured and consumed with small imported-target
# contracts standing in for installed binaries. No compiler is invoked.
for case in a.case or ['static','mono-static','shared','mono-shared','disabled']:
    root=a.work/case; root.mkdir(parents=True,exist_ok=True)
    mono=case.startswith('mono-'); static=case.endswith('static'); enabled=case!='disabled'
    typ='STATIC' if static else 'SHARED'
    targets=''
    libs='wxstc'
    if enabled:
        if mono:
            libs='wxstc;wxmono'
            targets=f'add_library(wx::wxmono {typ} IMPORTED)\nadd_library(wx::wxstc INTERFACE IMPORTED)\nset_target_properties(wx::wxstc PROPERTIES INTERFACE_LINK_LIBRARIES wx::wxmono)\n'
            owner='wx::wxmono'
        else:
            targets=f'add_library(wx::wxstc {typ} IMPORTED)\n'; owner='wx::wxstc'
        if static:
            targets+=f'set_target_properties({owner} PROPERTIES INTERFACE_LINK_LIBRARIES "$<LINK_ONLY:Scintilla::Core>;$<LINK_ONLY:Lexilla::Access>")\n'
    else:
        libs='wxcore'; targets='add_library(wx::wxcore STATIC IMPORTED)\n'
    (root/'wxWidgetsTargets.cmake').write_text(targets)
    (root/'FindThreads.cmake').write_text('add_library(Threads::Threads INTERFACE IMPORTED)\nset(Threads_FOUND TRUE)\n')
    (root/'ScintillaCoreConfig.cmake').write_text('add_library(Scintilla::Core INTERFACE IMPORTED)\n')
    (root/'LexillaConfig.cmake').write_text('add_library(Lexilla::Access INTERFACE IMPORTED)\n')
    want='ON' if enabled and static else 'OFF'
    cmake='''cmake_minimum_required(VERSION 3.16)
project(ConfigConsumer NONE)
include(CMakePackageConfigHelpers)
set(PROJECT_NAME wxWidgets)
set(wxUSE_STC ENABLED)
set(wxUSE_WEBREQUEST_CURL OFF)
set(wxLIB_TARGETS "LIBS")
set(wxLIB_BUILTIN_TARGETS "")
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}")
set(ScintillaCore_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
set(Lexilla_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
configure_package_config_file("${TEMPLATE}" "${CMAKE_CURRENT_BINARY_DIR}/package/wxWidgetsConfig.cmake" INSTALL_DESTINATION lib/cmake/wxWidgets)
configure_file(wxWidgetsTargets.cmake "${CMAKE_CURRENT_BINARY_DIR}/package/wxWidgetsTargets.cmake" COPYONLY)
find_package(wxWidgets CONFIG REQUIRED PATHS "${CMAKE_CURRENT_BINARY_DIR}/package" NO_DEFAULT_PATH)
if(WANT)
    if(NOT TARGET Scintilla::Core OR NOT TARGET Lexilla::Access)
        message(FATAL_ERROR "static wx export left STC dependency targets unresolved")
    endif()
else()
    if(TARGET Scintilla::Core OR TARGET Lexilla::Access)
        message(FATAL_ERROR "shared or STC-disabled wx requires unnecessary development providers")
    endif()
endif()
'''.replace('ENABLED','ON' if enabled else 'OFF').replace('LIBS',libs).replace('WANT',want)
    (root/'CMakeLists.txt').write_text(cmake)
    r=subprocess.run([str(a.cmake),'-S',str(root),'-B',str(root/'build'),'-DTEMPLATE='+str(a.template)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (root/'configure.log').write_text(r.stdout)
    print(case, 'PASS' if r.returncode==0 else 'FAIL')
    if r.returncode:
        print(r.stdout); raise SystemExit(r.returncode)
