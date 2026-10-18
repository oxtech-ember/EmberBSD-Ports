cmake_minimum_required(VERSION 3.10)
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed-provider checks using upstream tests.
project(EmberEigenUpstreamChecks LANGUAGES CXX)

if(NOT EXISTS "${EIGEN_UPSTREAM}/test/main.h")
  message(FATAL_ERROR "EIGEN_UPSTREAM must name the verified Eigen 5.0.1 source")
endif()
find_package(Eigen3 ${EIGEN_VERSION_REQUEST} CONFIG REQUIRED)
if(NOT Eigen3_VERSION VERSION_EQUAL "5.0.1")
  message(FATAL_ERROR "These checks require the installed Eigen 5.0.1 provider")
endif()
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
enable_testing()

add_executable(known-solve
  "${EIGEN_UPSTREAM}/doc/examples/Tutorial_PartialLU_solve.cpp")
target_link_libraries(known-solve PRIVATE Eigen3::Eigen)
add_test(NAME known-solve COMMAND "${CMAKE_COMMAND}"
  "-DEXAMPLE=$<TARGET_FILE:known-solve>"
  -P "${CMAKE_CURRENT_SOURCE_DIR}/known-solve.cmake")

foreach(entry "cholesky;3" "eigensolver_selfadjoint;7" "jacobisvd;10")
  list(GET entry 0 name)
  list(GET entry 1 part)
  add_executable(${name} "${EIGEN_UPSTREAM}/test/${name}.cpp")
  target_compile_definitions(${name} PRIVATE EIGEN_TEST_PART_${part}=1)
  target_link_libraries(${name} PRIVATE Eigen3::Eigen)
  add_test(NAME ${name} COMMAND ${name} r1 s1)
endforeach()
