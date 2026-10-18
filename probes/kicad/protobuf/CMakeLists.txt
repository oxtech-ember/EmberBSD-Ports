# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance.
cmake_minimum_required(VERSION 3.24)
project(emberbsd_protobuf_contract LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Protobuf 36.2.0 EXACT CONFIG REQUIRED)
if(NOT NATIVE_PROTOC OR NOT EXISTS "${NATIVE_PROTOC}")
  message(FATAL_ERROR "Set NATIVE_PROTOC to the matching native protoc")
endif()
execute_process(COMMAND "${NATIVE_PROTOC}" --version
  RESULT_VARIABLE protoc_result OUTPUT_VARIABLE protoc_version
  OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT protoc_result EQUAL 0 OR NOT protoc_version STREQUAL "libprotoc 36.2")
  message(FATAL_ERROR "The contracts require a working native protoc 36.2")
endif()
add_custom_command(OUTPUT contract.pb.cc contract.pb.h
  COMMAND "${NATIVE_PROTOC}" --cpp_out=${CMAKE_CURRENT_BINARY_DIR}
    -I "${CMAKE_CURRENT_SOURCE_DIR}" "${CMAKE_CURRENT_SOURCE_DIR}/contract.proto"
  DEPENDS contract.proto VERBATIM)
add_executable(emberbsd-protobuf-contract contract.cc contract.pb.cc)
target_compile_features(emberbsd-protobuf-contract PRIVATE cxx_std_17)
target_compile_options(emberbsd-protobuf-contract PRIVATE -Wall -Wextra -Wpedantic)
target_include_directories(emberbsd-protobuf-contract PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(emberbsd-protobuf-contract PRIVATE protobuf::libprotobuf)
add_executable(emberbsd-upb-oom-contract upb-oom-contract.c)
target_compile_features(emberbsd-upb-oom-contract PRIVATE c_std_11)
target_compile_options(emberbsd-upb-oom-contract PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(emberbsd-upb-oom-contract PRIVATE protobuf::libupb)
install(TARGETS emberbsd-protobuf-contract emberbsd-upb-oom-contract
  RUNTIME DESTINATION libexec/emberbsd-tests)
