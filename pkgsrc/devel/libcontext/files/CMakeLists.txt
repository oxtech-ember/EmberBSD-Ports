cmake_minimum_required(VERSION 3.16)
project(libcontext VERSION 20261029 LANGUAGES CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
add_library(context SHARED libcontext.cpp)
if(MSVC)
    enable_language(ASM_MASM)
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(ARM64|arm64|aarch64)$")
        target_sources(context PRIVATE make_arm64_aapcs_pe_armasm.asm jump_arm64_aapcs_pe_armasm.asm)
    elseif(CMAKE_SIZEOF_VOID_P EQUAL 8)
        target_sources(context PRIVATE make_x86_64_ms_pe_masm.asm jump_x86_64_ms_pe_masm.asm)
    else()
        target_sources(context PRIVATE make_i386_ms_pe_masm.asm jump_i386_ms_pe_masm.asm)
    endif()
endif()
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(context PRIVATE -fno-lto)
endif()
target_include_directories(context PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
set_target_properties(context PROPERTIES VERSION 20261029.0.0 SOVERSION 20261029
    WINDOWS_EXPORT_ALL_SYMBOLS ON)
install(TARGETS context EXPORT libcontextTargets LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES libcontext.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT libcontextTargets NAMESPACE libcontext:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/libcontext)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/libcontextConfig.cmake"
    "include(\"\${CMAKE_CURRENT_LIST_DIR}/libcontextTargets.cmake\")\n")
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/libcontextConfigVersion.cmake"
    VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/libcontextConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/libcontextConfigVersion.cmake" DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/libcontext)
install(FILES LICENSE.BOOSTv1_0 DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/libcontext)
