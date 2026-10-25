# Origin: EmberBSD contributors (AI-assisted).
cmake_minimum_required(VERSION 3.22)
project(simplecpp_abi_test LANGUAGES CXX)
find_package(simplecpp 1.9.1 EXACT CONFIG REQUIRED)

# These tests compile and link target programs. They never execute target code.
set(CMAKE_TRY_COMPILE_TARGET_TYPE EXECUTABLE)
try_compile(ABI_MATCH "${CMAKE_CURRENT_BINARY_DIR}/match"
    "${CMAKE_CURRENT_SOURCE_DIR}/match.cpp"
    LINK_LIBRARIES simplecpp::simplecpp OUTPUT_VARIABLE match_log)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/match.log" "${match_log}")
if(NOT ABI_MATCH)
    message(FATAL_ERROR "The installed SimpleCpp ABI consumer failed: ${match_log}")
endif()

try_compile(ABI_MISMATCH "${CMAKE_CURRENT_BINARY_DIR}/mismatch"
    "${CMAKE_CURRENT_SOURCE_DIR}/mismatch.cpp"
    LINK_LIBRARIES simplecpp::simplecpp OUTPUT_VARIABLE mismatch_log)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/mismatch.log" "${mismatch_log}")
if(ABI_MISMATCH OR NOT mismatch_log MATCHES "simplecpp: libstdc\\+\\+ debug ABI mismatch")
    message(FATAL_ERROR "The installed header did not reject the ABI mismatch: ${mismatch_log}")
endif()
message(STATUS "PASS: matching installed ABI links; mismatched STL mode is rejected")
