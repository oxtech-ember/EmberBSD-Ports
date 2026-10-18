# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.25)
project(EmberKiCadActualApi LANGUAGES CXX)
if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR
   NOT CMAKE_CXX_COMPILER_VERSION VERSION_EQUAL "16.2.0")
  message(FATAL_ERROR "Use the common GCC 16.2.0 compiler")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT EXISTS "${KICAD_SOURCE}/api/CMakeLists.txt" OR
   NOT IS_ABSOLUTE "${Protobuf_PROTOC_EXECUTABLE}" OR
   NOT EXISTS "${Protobuf_PROTOC_EXECUTABLE}")
  message(FATAL_ERROR "Use the prepared actual KiCad source and a real native protoc")
endif()
execute_process(COMMAND "${Protobuf_PROTOC_EXECUTABLE}" --version
  RESULT_VARIABLE protoc_status OUTPUT_VARIABLE protoc_version
  OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT protoc_status EQUAL 0 OR NOT protoc_version STREQUAL "libprotoc 36.2")
  message(FATAL_ERROR "The native generator must be protobuf 36.2")
endif()
find_package(Protobuf 36.2.0 EXACT CONFIG REQUIRED)
if(NOT Protobuf_VERSION VERSION_EQUAL "36.2.0")
  message(FATAL_ERROR "Use the selected protobuf 36.2 target SDK")
endif()
set(KICAD_CMAKE_MODULE_PATH "${KICAD_SOURCE}/cmake")
set(KICAD_LIB lib)
set(KICAD_DATA share/kicad)
set(KICMAKE_CFG_INTDIR "")
set(KICAD_USE_CMAKE_FINDPROTOBUF OFF)
add_subdirectory("${KICAD_SOURCE}/api" api)

add_executable(kiapi-version-contract version-contract.cc)
target_link_libraries(kiapi-version-contract PRIVATE kiapi)
target_compile_options(kiapi-version-contract PRIVATE -Wall -Wextra -Wpedantic)
target_include_directories(kiapi-version-contract PRIVATE "${KICAD_SOURCE}/include")
