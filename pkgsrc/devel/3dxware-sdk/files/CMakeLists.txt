cmake_minimum_required(VERSION 3.20)
project(TDxWare_SDK VERSION 4.0 LANGUAGES C CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

add_library(TDxNavlib STATIC src/navlib_stub.c src/navlib_load.cpp)
add_library(3DxWare::Navlib ALIAS TDxNavlib)
set_target_properties(TDxNavlib PROPERTIES EXPORT_NAME Navlib)
target_include_directories(TDxNavlib
  PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/inc")
target_compile_features(TDxNavlib PUBLIC cxx_std_11)

add_library(TDxWareHeaders INTERFACE)
add_library(3DxWare::headers ALIAS TDxWareHeaders)
set_target_properties(TDxWareHeaders PROPERTIES EXPORT_NAME headers)
target_include_directories(TDxWareHeaders INTERFACE
  "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>")
target_link_libraries(TDxNavlib PUBLIC TDxWareHeaders)

install(TARGETS TDxNavlib TDxWareHeaders EXPORT TDxWare_SDKTargets
  ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
  INCLUDES DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")
install(DIRECTORY inc/ DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
  FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(EXPORT TDxWare_SDKTargets NAMESPACE 3DxWare::
  DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/TDxWare_SDK")

configure_package_config_file(TDxWare_SDKConfig.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/TDxWare_SDKConfig.cmake"
  INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/TDxWare_SDK")
write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/TDxWare_SDKConfigVersion.cmake"
  VERSION "${PROJECT_VERSION}" COMPATIBILITY SameMajorVersion)
install(FILES
  "${CMAKE_CURRENT_BINARY_DIR}/TDxWare_SDKConfig.cmake"
  "${CMAKE_CURRENT_BINARY_DIR}/TDxWare_SDKConfigVersion.cmake"
  DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/TDxWare_SDK")
