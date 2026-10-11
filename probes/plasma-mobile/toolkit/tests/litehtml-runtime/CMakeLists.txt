# SPDX-License-Identifier: BSD-2-Clause
cmake_minimum_required(VERSION 3.30)
project(EmberLitehtmlEncodings LANGUAGES CXX)
find_package(litehtml CONFIG REQUIRED)
find_package(GTest 1.18.0 EXACT CONFIG REQUIRED)
add_executable(litehtml-runtime "${UPSTREAM_TEST_SOURCE}/encodings_test.cpp" css-flags.cpp)
target_compile_features(litehtml-runtime PRIVATE cxx_std_17)
target_link_libraries(litehtml-runtime PRIVATE litehtml GTest::gtest_main)
