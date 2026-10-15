# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed common dependency contract.
cmake_minimum_required(VERSION 3.22)
project(ember_ompl_dependency_contract LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT IS_ABSOLUTE "${DEPENDENCY_PREFIX}")
    message(FATAL_ERROR "Set an absolute DEPENDENCY_PREFIX")
endif()
find_package(Eigen3 5.0.1 EXACT CONFIG REQUIRED
    PATHS "${DEPENDENCY_PREFIX}/share/eigen3/cmake" NO_DEFAULT_PATH)
set(Boost_DIR "${DEPENDENCY_PREFIX}/lib/cmake/Boost-1.92.0")
find_package(Boost 1.92.0 EXACT CONFIG REQUIRED COMPONENTS serialization program_options)
add_executable(ompl-dependency-contract contract.cc)
target_compile_features(ompl-dependency-contract PRIVATE cxx_std_17)
target_compile_options(ompl-dependency-contract PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(ompl-dependency-contract PRIVATE
    Eigen3::Eigen Boost::serialization Boost::program_options)
enable_testing()
add_test(NAME ompl-common-dependencies COMMAND ompl-dependency-contract)
set_tests_properties(ompl-common-dependencies PROPERTIES TIMEOUT 30)
