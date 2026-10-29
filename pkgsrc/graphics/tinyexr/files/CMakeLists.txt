cmake_minimum_required(VERSION 3.16)
project(tinyexr VERSION 3.2.0 LANGUAGES C CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
find_package(ZLIB REQUIRED)
find_package(Threads REQUIRED)
find_library(ZSTD_LIBRARY NAMES zstd REQUIRED)
find_library(LIBDEFLATE_LIBRARY NAMES deflate REQUIRED)
file(GLOB EXR_SOURCES CONFIGURE_DEPENDS "src/*.c")
add_library(tinyexr3 ${EXR_SOURCES})
target_compile_features(tinyexr3 PRIVATE c_std_11)
target_include_directories(tinyexr3 PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}> PRIVATE src)
target_compile_definitions(tinyexr3 PRIVATE EXR_USE_LIBDEFLATE EXR_ZLIB_DEFAULT_LIBDEFLATE=1)
target_link_libraries(tinyexr3 PRIVATE ${ZSTD_LIBRARY} ${LIBDEFLATE_LIBRARY} ${CMAKE_DL_LIBS})
if(NOT WIN32)
  target_link_libraries(tinyexr3 PRIVATE m)
endif()
add_library(tinyexr legacy.cc)
target_compile_features(tinyexr PRIVATE cxx_std_11)
target_include_directories(tinyexr PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}> $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_link_libraries(tinyexr PRIVATE ZLIB::ZLIB Threads::Threads)
set_target_properties(tinyexr tinyexr3 PROPERTIES VERSION ${PROJECT_VERSION} SOVERSION ${PROJECT_VERSION_MAJOR})
install(TARGETS tinyexr tinyexr3 EXPORT TinyEXRTargets LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR} ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES tinyexr.h exr_reader.hh streamreader.hh include/exr.h include/exr_gpu.h include/exr_vk.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

configure_package_config_file(${CMAKE_CURRENT_SOURCE_DIR}/TinyEXRConfig.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/TinyEXRConfig.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/TinyEXR)
write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/TinyEXRConfigVersion.cmake
  VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(EXPORT TinyEXRTargets NAMESPACE TinyEXR:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/TinyEXR)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/TinyEXRConfig.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/TinyEXRConfigVersion.cmake
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/TinyEXR)
