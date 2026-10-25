# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Configure only through the independently accepted SDK tool selection.
cmake_minimum_required(VERSION 3.29)
project(EmberDarwinInitial C)
set(INITIAL_TEST_OPERATION "static" CACHE STRING "Fixed optional-operation control")

if(INITIAL_TEST_OPERATION STREQUAL "exports-global")
  set(CMAKE_SHARED_LIBRARY_ENABLE_EXPORTS ON)
elseif(INITIAL_TEST_OPERATION STREQUAL "exports-executable")
  # This legacy variable initializes executable exports, not shared TBD output.
  set(CMAKE_ENABLE_EXPORTS ON)
endif()

if(INITIAL_TEST_OPERATION STREQUAL "static")
  add_library(example STATIC fixture.c)
  install(TARGETS example ARCHIVE DESTINATION lib)
elseif(INITIAL_TEST_OPERATION MATCHES "^exports-(property|global)$")
  add_library(example SHARED fixture.c)
  if(INITIAL_TEST_OPERATION STREQUAL "exports-property")
    set_property(TARGET example PROPERTY ENABLE_EXPORTS ON)
  endif()
elseif(INITIAL_TEST_OPERATION STREQUAL "exports-executable")
  add_executable(example fixture.c)
elseif(INITIAL_TEST_OPERATION STREQUAL "install-name")
  add_library(example SHARED fixture.c)
  set_target_properties(example PROPERTIES
    BUILD_WITH_INSTALL_NAME_DIR OFF
    INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib")
  install(TARGETS example LIBRARY DESTINATION lib)
elseif(INITIAL_TEST_OPERATION STREQUAL "rpath")
  add_executable(example fixture.c)
  set_target_properties(example PROPERTIES
    BUILD_WITH_INSTALL_RPATH OFF
    SKIP_BUILD_RPATH OFF
    BUILD_RPATH "${CMAKE_BINARY_DIR}/build-runtime"
    INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")
  install(TARGETS example RUNTIME DESTINATION bin)
else()
  message(FATAL_ERROR "Unknown fixed INITIAL_TEST_OPERATION")
endif()

# CMAKE_EXECUTABLE_ENABLE_EXPORTS is the modern executable-only input too.
# The property/global shared cases require TAPI. Executable exports do not.
