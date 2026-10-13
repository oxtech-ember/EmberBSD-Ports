# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Export the real source include expressions.
cmake_minimum_required(VERSION 3.19)
project(FcitxExportMetadata VERSION 5.1.23 LANGUAGES NONE)
set(CMAKE_INSTALL_LIBDIR lib)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
set(FCITX_VERSION 5.1.23)
set(FCITX_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")
set(FCITX_INSTALL_LIBDIR "${CMAKE_INSTALL_FULL_LIBDIR}")
set(FCITX_INSTALL_MODULE_HEADER_DIR "${CMAKE_INSTALL_FULL_INCLUDEDIR}/Fcitx5/Module/fcitx-module")
set(FCITX_INSTALL_INCLUDEDIR "${CMAKE_INSTALL_FULL_INCLUDEDIR}")
include("${FCITX_SOURCE}/src/lib/fcitx-utils/Fcitx5Macros.cmake")

foreach(component Utils Config Core)
    if(component STREQUAL "Utils")
        set(directory fcitx-utils)
    elseif(component STREQUAL "Config")
        set(directory fcitx-config)
    else()
        set(directory fcitx)
    endif()
    file(STRINGS "${FCITX_SOURCE}/src/lib/${directory}/CMakeLists.txt" declarations
        REGEX "INSTALL_INTERFACE:")
    list(LENGTH declarations count)
    if(NOT count EQUAL 1)
        message(FATAL_ERROR "Unexpected install interface count: ${component}")
    endif()
    string(REGEX MATCH "\\$<INSTALL_INTERFACE:[^>]+>" expression "${declarations}")
    # Expand exactly the original source expression in the install context.
    string(CONFIGURE "${expression}" expression)
    add_library(Fcitx5${component} INTERFACE)
    set_target_properties(Fcitx5${component} PROPERTIES EXPORT_NAME ${component})
    add_library(Fcitx5::${component} ALIAS Fcitx5${component})
    target_include_directories(Fcitx5${component} INTERFACE "${expression}")
    if(component STREQUAL "Config")
        target_link_libraries(Fcitx5Config INTERFACE Fcitx5::Utils)
    elseif(component STREQUAL "Core")
        target_link_libraries(Fcitx5Core INTERFACE Fcitx5::Config Fcitx5::Utils)
    endif()
    install(TARGETS Fcitx5${component} EXPORT Fcitx5${component}Targets)
    install(EXPORT Fcitx5${component}Targets NAMESPACE Fcitx5::
        DESTINATION lib/cmake/Fcitx5${component})
    configure_package_config_file(
        "${FCITX_SOURCE}/src/lib/${directory}/Fcitx5${component}Config.cmake.in"
        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5${component}Config.cmake"
        INSTALL_DESTINATION lib/cmake/Fcitx5${component})
    write_basic_package_version_file(
        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5${component}ConfigVersion.cmake"
        VERSION 5.1.23 COMPATIBILITY SameMajorVersion)
    install(FILES
        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5${component}Config.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/Fcitx5${component}ConfigVersion.cmake"
        DESTINATION lib/cmake/Fcitx5${component})
    install(DIRECTORY "${FCITX_SOURCE}/src/lib/${directory}"
        DESTINATION include/Fcitx5/${component} FILES_MATCHING PATTERN "*.h")
endforeach()
install(FILES "${FCITX_SOURCE}/src/lib/fcitx-utils/Fcitx5Macros.cmake"
    "${FCITX_SOURCE}/src/lib/fcitx-utils/Fcitx5ModuleTemplate.cmake.in"
    DESTINATION lib/cmake/Fcitx5Utils)

# This is the unchanged upstream macro, not a replacement module exporter.
fcitx5_export_module(Emoji TARGET emoji INSTALL
    BUILD_INCLUDE_DIRECTORIES "${FCITX_SOURCE}/src/modules/emoji"
    HEADERS "${FCITX_SOURCE}/src/modules/emoji/emoji_public.h")
get_target_property(build_includes Fcitx5::Module::Emoji INTERFACE_INCLUDE_DIRECTORIES)
if(NOT build_includes STREQUAL "${FCITX_SOURCE}/src/modules/emoji")
    message(FATAL_ERROR "Module build interface changed")
endif()
