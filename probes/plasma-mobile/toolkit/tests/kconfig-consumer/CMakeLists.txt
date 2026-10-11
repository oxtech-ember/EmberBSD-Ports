# SPDX-License-Identifier: BSD-2-Clause
cmake_minimum_required(VERSION 3.30)
project(EmberKConfigConsumer LANGUAGES CXX)
find_package(Qt6 6.12.0 EXACT REQUIRED COMPONENTS Core)
find_package(KF6Config 6.31.0 EXACT REQUIRED)
# Independent Frameworks dependencies can import the same generator twice.
find_package(KF6Config 6.31.0 EXACT REQUIRED)
get_target_property(generator KF6::kconfig_compiler IMPORTED_LOCATION)
execute_process(COMMAND "${generator}" --version OUTPUT_VARIABLE version
                RESULT_VARIABLE status OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT status EQUAL 0 OR NOT version STREQUAL "kconfig_compiler 6.31.0")
    message(FATAL_ERROR "Matching native KConfig 6.31 generator required")
endif()
add_executable(kconfig-consumer main.cpp)
target_include_directories(kconfig-consumer PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
kconfig_add_kcfg_files(kconfig-consumer settings.kcfgc)
target_link_libraries(kconfig-consumer PRIVATE Qt6::Core KF6::ConfigCore)
target_compile_features(kconfig-consumer PRIVATE cxx_std_20)
