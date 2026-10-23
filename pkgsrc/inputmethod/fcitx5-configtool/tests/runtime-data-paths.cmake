# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.16)
project(ConfigtoolDataPaths NONE)

list(PREPEND CMAKE_MODULE_PATH "${SOURCE}/cmake")
# Use the real upstream discovery modules with controlled .pc and data files.
# Do not fall back to unrelated files installed on the machine running the test.
set(CMAKE_FIND_USE_CMAKE_SYSTEM_PATH FALSE)
set(CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH FALSE)
set(CMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH FALSE)
find_package(IsoCodes REQUIRED)
find_package(XKeyboardConfig REQUIRED)

foreach(code 2 3 5)
    set(expected "${HOST_PREFIX}/share/iso-codes/json/iso_639-${code}.json")
    if(NOT "${ISOCODES_ISO639_${code}_JSON}" STREQUAL "${expected}")
        message(FATAL_ERROR "Unexpected ISO discovery path for ${code}")
    endif()
endforeach()
if(NOT XKEYBOARDCONFIG_XKBBASE STREQUAL "${HOST_PREFIX}/share/X11/xkb" OR
   NOT XKEYBOARDCONFIG_DATADIR STREQUAL "${HOST_PREFIX}/share")
    message(FATAL_ERROR "Unexpected XKB discovery paths")
endif()

# Only run the production runtime-path include, immediately before config.h.
# The complete Qt/KF application build remains a separate package check.
file(READ "${SOURCE}/CMakeLists.txt" root)
if(PATCHED)
    string(FIND "${root}" "include(Fcitx5RuntimeDataPaths)\nconfigure_file(config.h.in config.h)" position)
    if(position EQUAL -1)
        message(FATAL_ERROR "Missing production runtime-path integration")
    endif()
    include(Fcitx5RuntimeDataPaths)
endif()
configure_file("${SOURCE}/config.h.in" "${CMAKE_CURRENT_BINARY_DIR}/config.h")
file(READ "${CMAKE_CURRENT_BINARY_DIR}/config.h" config)
foreach(code 2 3 5)
    set(variable "ISOCODES_ISO639_${code}_JSON")
    set(expected "${RUNTIME_PREFIX}/share/iso-codes/json/iso_639-${code}.json")
    string(FIND "${config}" "#define ${variable} \"${expected}\"" position)
    if(position EQUAL -1)
        message(FATAL_ERROR "Runtime path mismatch: ${variable}")
    endif()
    if(NOT "${${variable}}" STREQUAL "${HOST_PREFIX}/share/iso-codes/json/iso_639-${code}.json")
        message(FATAL_ERROR "ISO discovery path was overwritten")
    endif()
endforeach()
string(FIND "${config}" "#define XKEYBOARDCONFIG_XKBBASE \"${RUNTIME_PREFIX}/share/X11/xkb\"" position)
if(position EQUAL -1)
    message(FATAL_ERROR "Runtime path mismatch: XKEYBOARDCONFIG_XKBBASE")
endif()
if(NOT XKEYBOARDCONFIG_XKBBASE STREQUAL "${HOST_PREFIX}/share/X11/xkb" OR
   NOT XKEYBOARDCONFIG_DATADIR STREQUAL "${HOST_PREFIX}/share")
    message(FATAL_ERROR "XKB discovery paths were overwritten")
endif()
