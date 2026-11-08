cmake_minimum_required(VERSION 3.16)
project(sundown VERSION 1.16.0 LANGUAGES C)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
add_library(sundown SHARED
    md_parser/markdown.c md_parser/stack.c md_parser/buffer.c md_parser/autolink.c
    html_formatter/html.c html_formatter/html_smartypants.c
    html_formatter/houdini_html_e.c html_formatter/houdini_href_e.c)
target_include_directories(sundown PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/md_parser>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/html_formatter>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/sundown>)
set_target_properties(sundown PROPERTIES VERSION 1.16.0 SOVERSION 1)
install(TARGETS sundown EXPORT sundownTargets LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(DIRECTORY md_parser/ html_formatter/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/sundown
    FILES_MATCHING PATTERN "*.h")
install(EXPORT sundownTargets NAMESPACE sundown:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/sundown)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/sundownConfig.cmake"
    "include(\"\${CMAKE_CURRENT_LIST_DIR}/sundownTargets.cmake\")\n")
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/sundownConfigVersion.cmake"
    VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/sundownConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/sundownConfigVersion.cmake" DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/sundown)
install(FILES html_formatter/LICENSE.txt DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/sundown)
