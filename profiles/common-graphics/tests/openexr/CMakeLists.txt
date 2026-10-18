# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Link only the installed public package.
cmake_minimum_required(VERSION 3.22)
project(ember_openexr_contract LANGUAGES CXX)
find_package(OpenEXR 3.5.2 EXACT CONFIG REQUIRED)
add_executable(openexr-roundtrip roundtrip.cpp)
target_compile_features(openexr-roundtrip PRIVATE cxx_std_17)
target_compile_options(openexr-roundtrip PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(openexr-roundtrip PRIVATE OpenEXR::OpenEXR OpenEXR::OpenEXRCore)
install(TARGETS openexr-roundtrip RUNTIME DESTINATION bin)
