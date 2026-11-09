# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); upstream src/makefile source split.
cmake_minimum_required(VERSION 3.16)
project(Lexilla VERSION ${LEXILLA_VERSION} LANGUAGES CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
find_package(ScintillaCore CONFIG REQUIRED)
file(READ version.txt archive_version)
string(STRIP "${archive_version}" archive_version)
string(REPLACE "." "" expected_version "${PROJECT_VERSION}")
if(NOT archive_version STREQUAL expected_version)
    message(FATAL_ERROR "Lexilla source version differs from the selected recipe")
endif()

# Keep the upstream generated catalogue and all lexer implementations together.
file(GLOB lexer_sources CONFIGURE_DEPENDS "lexers/Lex*.cxx" "lexlib/*.cxx")
add_library(lexilla SHARED src/Lexilla.cxx ${lexer_sources})
add_library(Lexilla::Lexilla ALIAS lexilla)
set_target_properties(lexilla PROPERTIES EXPORT_NAME Lexilla VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR} POSITION_INDEPENDENT_CODE ON
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON CXX_EXTENSIONS OFF)
target_compile_features(lexilla PUBLIC cxx_std_17)
target_include_directories(lexilla PRIVATE lexlib)
target_include_directories(lexilla PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/lexilla>)
# ILexer5 is a header interface: never pull Scintilla's editing archive into Lexilla.
target_link_libraries(lexilla PUBLIC Scintilla::Headers)
# Upstream's loadable-lexer access layer is shared by frontend recipes too.
# PIC archive keeps this C++ helper private to each frontend DSO; the lexer
# implementations remain in the single shared lexilla library.
add_library(lexilla-access STATIC access/LexillaAccess.cxx)
add_library(Lexilla::Access ALIAS lexilla-access)
# Upstream direct-call mode; the selected provider is still the shared DSO.
target_compile_definitions(lexilla-access PRIVATE LEXILLA_STATIC)
set_target_properties(lexilla-access PROPERTIES EXPORT_NAME Access
    POSITION_INDEPENDENT_CODE ON CXX_EXTENSIONS OFF)
target_include_directories(lexilla-access PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/access>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/lexilla>)
target_link_libraries(lexilla-access PUBLIC Lexilla::Lexilla ${CMAKE_DL_LIBS})
install(TARGETS lexilla lexilla-access EXPORT LexillaTargets LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES include/Lexilla.h include/SciLexer.h include/LexicalStyles.iface access/LexillaAccess.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/lexilla)
install(FILES License.txt DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/lexilla)
install(EXPORT LexillaTargets NAMESPACE Lexilla:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Lexilla)
configure_package_config_file(LexillaConfig.cmake.in "${CMAKE_CURRENT_BINARY_DIR}/LexillaConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Lexilla)
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/LexillaConfigVersion.cmake"
    VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/LexillaConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/LexillaConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Lexilla)
set(LEXILLA_DL_LIBS "")
foreach(dl_lib IN LISTS CMAKE_DL_LIBS)
    string(APPEND LEXILLA_DL_LIBS " -l${dl_lib}")
endforeach()
foreach(pc lexilla lexilla-access)
    configure_file(${pc}.pc.in ${pc}.pc @ONLY)
    install(FILES "${CMAKE_CURRENT_BINARY_DIR}/${pc}.pc" DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)
endforeach()

option(BUILD_TESTING "Build provider and upstream lexer tests" OFF)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(emberbsd-tests)
    add_executable(lexilla-upstream-tests test/TestLexers.cxx test/TestDocument.cxx)
    target_include_directories(lexilla-upstream-tests PRIVATE test access)
    # Upstream's direct-call mode works with a linked DSO as well as its archive.
    target_compile_definitions(lexilla-upstream-tests PRIVATE LEXILLA_STATIC)
    target_compile_features(lexilla-upstream-tests PRIVATE cxx_std_20)
    target_link_libraries(lexilla-upstream-tests PRIVATE Lexilla::Access)
    add_test(NAME lexilla-upstream COMMAND lexilla-upstream-tests)
    set_tests_properties(lexilla-upstream PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/test")
endif()
