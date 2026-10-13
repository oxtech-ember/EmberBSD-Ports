# SPDX-License-Identifier: BSD-2-Clause
cmake_minimum_required(VERSION 3.30)
project(plasma_gamecontroller_sdl3_tests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_AUTOMOC ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
find_package(Qt6 6.12 CONFIG REQUIRED COMPONENTS Core Gui Qml Test)
find_package(KF6I18n 6.31 CONFIG REQUIRED)
find_package(SDL3 3.4.18 CONFIG REQUIRED)
find_library(UDEV_LIBRARY NAMES udev REQUIRED)
if(NOT IS_DIRECTORY "${GAMECONTROLLER_SOURCE}")
  message(FATAL_ERROR "Set GAMECONTROLLER_SOURCE to the patched gamecontroller source directory")
endif()
add_executable(device-test device-test.cpp logging.cpp
  "${GAMECONTROLLER_SOURCE}/device.cpp"
  "${GAMECONTROLLER_SOURCE}/devicemodel.cpp"
  "${GAMECONTROLLER_SOURCE}/udevmatcher.cpp")
target_include_directories(device-test PRIVATE "${GAMECONTROLLER_SOURCE}" "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_definitions(device-test PRIVATE SDL_DISABLE_OLD_NAMES TRANSLATION_DOMAIN="kcm_gamecontroller")
target_link_libraries(device-test PRIVATE Qt6::Core Qt6::Gui Qt6::Qml Qt6::Test KF6::I18n SDL3::SDL3 "${UDEV_LIBRARY}")
if(EMBER_TEST_EXTRA_FLAGS)
  target_compile_options(device-test PRIVATE ${EMBER_TEST_EXTRA_FLAGS})
endif()
enable_testing()
add_test(NAME device-sdl3 COMMAND device-test)

if(CMAKE_CROSSCOMPILING)
  if(NOT EXISTS "${CMAKE_SYSROOT}/usr/pkg/gcc16/lib/libstdc++.so")
    message(FATAL_ERROR "The common GCC16 runtime is missing from the sysroot")
  endif()
  target_link_directories(device-test BEFORE PRIVATE "${CMAKE_SYSROOT}/usr/pkg/gcc16/lib")
  set_target_properties(device-test PROPERTIES BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "/usr/pkg/lib;/usr/pkg/qt6/lib;/usr/pkg/gcc16/lib")
  target_link_options(device-test PRIVATE
    "LINKER:-rpath-link,${CMAKE_SYSROOT}/usr/pkg/lib:${CMAKE_SYSROOT}/usr/pkg/qt6/lib")
endif()

option(EMBER_TEST_UBSAN "Check undefined behavior with Clang trap instrumentation" OFF)
if(EMBER_TEST_UBSAN)
  if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    message(FATAL_ERROR "EMBER_TEST_UBSAN requires Clang")
  endif()
  target_compile_options(device-test PRIVATE -fsanitize=undefined -fsanitize-trap=undefined)
endif()
