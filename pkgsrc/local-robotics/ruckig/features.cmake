# SPDX-License-Identifier: MIT
# Origin: EmberBSD, AI-assisted shared native and cross Ruckig build policy.
set(CMAKE_BUILD_TYPE Release CACHE STRING "Package build type")
set(CMAKE_INSTALL_LIBDIR lib CACHE PATH "Library and CMake export directory")
set(BUILD_SHARED_LIBS ON CACHE BOOL "Preserve the upstream shared library")
set(BUILD_TESTS ON CACHE BOOL "Build all upstream target test groups")
foreach(option IN ITEMS BUILD_CLOUD_CLIENT BUILD_PYTHON_MODULE BUILD_EXAMPLES BUILD_BENCHMARK)
    set(${option} OFF CACHE BOOL "Local trajectory library package")
endforeach()
