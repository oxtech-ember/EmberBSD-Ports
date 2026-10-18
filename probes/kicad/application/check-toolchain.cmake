# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Inspect the supplied real toolchain before KiCad runs any discovery commands.
include("${EMBER_TOOLCHAIN}")
if(NOT CMAKE_SYSTEM_NAME STREQUAL "NetBSD" OR
   NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
    message(FATAL_ERROR "Expected the AArch64 NetBSD toolchain for EmberBSD")
endif()
if(NOT CMAKE_SYSROOT STREQUAL EMBER_SYSROOT)
    message(FATAL_ERROR "Toolchain sysroot differs from the requested sysroot")
endif()
if(NOT CMAKE_C_COMPILER STREQUAL EMBER_CC OR
   NOT CMAKE_CXX_COMPILER STREQUAL EMBER_CXX)
    message(FATAL_ERROR "Toolchain compilers differ from CC/CXX")
endif()
if(NOT CMAKE_FIND_ROOT_PATH_MODE_PROGRAM STREQUAL "NEVER")
    message(FATAL_ERROR "Native generators require program lookup outside the target root")
endif()
foreach(kind LIBRARY INCLUDE PACKAGE)
    if(NOT CMAKE_FIND_ROOT_PATH_MODE_${kind} STREQUAL "ONLY")
        message(FATAL_ERROR "Target ${kind} lookup must stay inside the target root")
    endif()
endforeach()
