# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); consume installed package metadata.
cmake_minimum_required(VERSION 3.25)
project(EmberAbseilConsumer LANGUAGES CXX)
find_package(absl 20260817 CONFIG REQUIRED)
add_executable(abseil-consumer consumer.cc)
target_compile_features(abseil-consumer PRIVATE cxx_std_17)
target_link_libraries(abseil-consumer PRIVATE absl::strings absl::stacktrace)
set_target_properties(abseil-consumer PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
# The frame-pointer unwinder needs a frame chain in the consumer too.
target_compile_options(abseil-consumer PRIVATE -fno-omit-frame-pointer)
