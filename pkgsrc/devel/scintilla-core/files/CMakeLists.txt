# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); upstream gtk/makefile core split.
cmake_minimum_required(VERSION 3.16)
project(ScintillaCore VERSION ${SCINTILLA_VERSION} LANGUAGES CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
set(THREADS_PREFER_PTHREAD_FLAG TRUE)
find_package(Threads REQUIRED)
file(READ version.txt archive_version)
string(STRIP "${archive_version}" archive_version)
string(REPLACE "." "" expected_version "${PROJECT_VERSION}")
if(NOT archive_version STREQUAL expected_version)
    message(FATAL_ERROR "Scintilla source version differs from the selected recipe")
endif()

# src/ is exactly upstream SRC_OBJS plus ScintillaBase, without a widget backend.
file(GLOB core_sources CONFIGURE_DEPENDS "src/*.cxx")
add_library(scintilla-core STATIC ${core_sources})
add_library(Scintilla::Core ALIAS scintilla-core)
set_target_properties(scintilla-core PROPERTIES
    EXPORT_NAME Core POSITION_INDEPENDENT_CODE ON CXX_EXTENSIONS OFF)
target_compile_features(scintilla-core PUBLIC cxx_std_17)
target_compile_definitions(scintilla-core PRIVATE SCINTILLA_CORE $<$<NOT:$<CONFIG:Debug>>:NDEBUG>)

add_library(scintilla-headers INTERFACE)
add_library(Scintilla::Headers ALIAS scintilla-headers)
set_target_properties(scintilla-headers PROPERTIES EXPORT_NAME Headers)
target_include_directories(scintilla-headers INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/scintilla-core>)
target_link_libraries(scintilla-core PUBLIC scintilla-headers Threads::Threads)
target_include_directories(scintilla-core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/scintilla-core/private>)

install(TARGETS scintilla-core scintilla-headers EXPORT ScintillaCoreTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/scintilla-core
    FILES_MATCHING PATTERN "*.h" PATTERN "Scintilla.iface"
    PATTERN "ScintillaWidget.h" EXCLUDE PATTERN "ScintillaCall.h" EXCLUDE)
install(DIRECTORY src/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/scintilla-core/private
    FILES_MATCHING PATTERN "*.h")
install(FILES License.txt DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/scintilla-core)
install(EXPORT ScintillaCoreTargets NAMESPACE Scintilla::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ScintillaCore)
configure_package_config_file(ScintillaCoreConfig.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/ScintillaCoreConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ScintillaCore)
# Core's C++ private classes are not a stable cross-release ABI.
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/ScintillaCoreConfigVersion.cmake"
    VERSION ${PROJECT_VERSION} COMPATIBILITY ExactVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/ScintillaCoreConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/ScintillaCoreConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ScintillaCore)
foreach(pc scintilla-core scintilla-headers)
    configure_file(${pc}.pc.in ${pc}.pc @ONLY)
    install(FILES "${CMAKE_CURRENT_BINARY_DIR}/${pc}.pc"
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)
endforeach()

option(BUILD_TESTING "Build core provider contract tests" OFF)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(emberbsd-tests)
endif()
