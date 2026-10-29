# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
cmake_minimum_required(VERSION 3.15)
project(xatlas LANGUAGES CXX)
include(GNUInstallDirs)
find_package(Threads REQUIRED)
add_library(xatlas STATIC source/xatlas/xatlas.cpp)
target_link_libraries(xatlas PUBLIC Threads::Threads)
target_include_directories(xatlas PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/source/xatlas> $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
install(TARGETS xatlas EXPORT xatlasTargets ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES source/xatlas/xatlas.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT xatlasTargets NAMESPACE xatlas:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/xatlas)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/xatlasConfig.cmake "include(CMakeFindDependencyMacro)\nfind_dependency(Threads)\ninclude(\"\${CMAKE_CURRENT_LIST_DIR}/xatlasTargets.cmake\")\n")
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/xatlasConfig.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/xatlas)
