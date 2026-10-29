# Origin: EmberBSD contributors (AI-assisted); integrates the Open3DGC snapshot.
cmake_minimum_required(VERSION 3.16)
project(open3dgc LANGUAGES CXX)
include(GNUInstallDirs)
add_library(open3dgc o3dgcArithmeticCodec.cpp o3dgcDynamicVectorDecoder.cpp
    o3dgcDynamicVectorEncoder.cpp o3dgcTools.cpp o3dgcTriangleFans.cpp)
set_target_properties(open3dgc PROPERTIES VERSION 0.0.0 SOVERSION 0)
target_include_directories(open3dgc PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/..>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
install(TARGETS open3dgc EXPORT open3dgcTargets)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/Open3DGC
    FILES_MATCHING PATTERN "*.h" PATTERN "*.inl")
install(EXPORT open3dgcTargets NAMESPACE open3dgc:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/open3dgc)
install(FILES open3dgcConfig.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/open3dgc)
enable_testing()
add_executable(open3dgc-roundtrip roundtrip.cpp)
target_link_libraries(open3dgc-roundtrip PRIVATE open3dgc)
add_test(NAME open3dgc-roundtrip COMMAND open3dgc-roundtrip)
