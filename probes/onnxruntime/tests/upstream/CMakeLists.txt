cmake_minimum_required(VERSION 3.28)
project(EmberBSDOnnxUpstreamControls LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

foreach(required ORT_SOURCE_DIR ORT_BUILD_DIR GTEST_SOURCE_DIR)
  if(NOT IS_ABSOLUTE "${${required}}" OR NOT IS_DIRECTORY "${${required}}")
    message(FATAL_ERROR "${required} must name an existing absolute directory")
  endif()
endforeach()

find_package(Threads REQUIRED)
find_package(Eigen3 5.0.1 CONFIG REQUIRED)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
set(gtest_build_tests OFF CACHE BOOL "" FORCE)
set(gtest_build_samples OFF CACHE BOOL "" FORCE)
set(BUILD_GMOCK OFF CACHE BOOL "" FORCE)
add_subdirectory("${GTEST_SOURCE_DIR}" googletest EXCLUDE_FROM_ALL)

# These are the actual production archives from the runtime build.
file(GLOB_RECURSE ort_archives CONFIGURE_DEPENDS "${ORT_BUILD_DIR}/*.a")
list(FILTER ort_archives EXCLUDE REGEX "/CMakeFiles/|/googletest/|/googlemock/")
foreach(required_archive onnxruntime_common onnxruntime_mlas)
  set(found FALSE)
  foreach(archive IN LISTS ort_archives)
    if(archive MATCHES "/lib${required_archive}\\.a$")
      set(found TRUE)
    endif()
  endforeach()
  if(NOT found)
    message(FATAL_ERROR "Production archive lib${required_archive}.a is absent")
  endif()
endforeach()

# Keep every selected upstream source unchanged. The upstream MLAS main also
# registers the short transpose controls, including real two-thread cases.
set(upstream_sources
  onnxruntime/test/common/narrow_test.cc
  onnxruntime/test/common/safeint_test.cc
  onnxruntime/test/common/string_utils_test.cc
  onnxruntime/test/common/utf8_util_test.cc
  onnxruntime/test/mlas/unittest/test_conv_prepare_safeint.cpp
  onnxruntime/test/mlas/unittest/test_transpose.cpp
  onnxruntime/test/mlas/unittest/test_main.cpp)
list(TRANSFORM upstream_sources PREPEND "${ORT_SOURCE_DIR}/")
add_executable(onnx-upstream-controls ${upstream_sources})

# Preserve definitions that affect the internal ThreadPool/Eigen ABI.
file(READ "${ORT_BUILD_DIR}/compile_commands.json" production_database)
string(JSON production_count LENGTH "${production_database}")
math(EXPR production_last "${production_count} - 1")
set(found_threadpool_context FALSE)
foreach(index RANGE 0 ${production_last})
  string(JSON production_source GET "${production_database}" ${index} file)
  if(production_source MATCHES "/onnxruntime/core/common/threadpool\\.cc$")
    string(JSON production_command GET "${production_database}" ${index} command)
    separate_arguments(production_arguments UNIX_COMMAND "${production_command}")
    foreach(argument IN LISTS production_arguments)
      if(argument MATCHES "^-D(.+)$")
        target_compile_definitions(onnx-upstream-controls PRIVATE "${CMAKE_MATCH_1}")
      elseif(argument STREQUAL "-fno-rtti")
        target_compile_options(onnx-upstream-controls PRIVATE "${argument}")
      endif()
    endforeach()
    set(found_threadpool_context TRUE)
    break()
  endif()
endforeach()
if(NOT found_threadpool_context)
  message(FATAL_ERROR "Production ThreadPool compile context is absent")
endif()
target_include_directories(onnx-upstream-controls PRIVATE
  "${ORT_SOURCE_DIR}/include/onnxruntime"
  "${ORT_SOURCE_DIR}/onnxruntime"
  "${ORT_SOURCE_DIR}/onnxruntime/core/mlas/inc"
  "${ORT_BUILD_DIR}"
  "${ORT_BUILD_DIR}/_deps/abseil_cpp-src"
  "${ORT_BUILD_DIR}/_deps/gsl-src/include"
  "${ORT_BUILD_DIR}/_deps/safeint-src"
  "${ORT_BUILD_DIR}/_deps/flatbuffers-src/include"
  "${ORT_BUILD_DIR}/_deps/onnx-src"
  "${ORT_BUILD_DIR}/_deps/onnx-build"
  "${ORT_BUILD_DIR}/_deps/protobuf-src/src")
target_link_libraries(onnx-upstream-controls PRIVATE
  "-Wl,--start-group" ${ort_archives} "-Wl,--end-group"
  GTest::gtest Eigen3::Eigen Threads::Threads ${CMAKE_DL_LIBS})

file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/production-archives.txt"
  CONTENT "$<JOIN:${ort_archives},\n>\n")
enable_testing()
add_test(NAME onnx-upstream-controls COMMAND onnx-upstream-controls)
set_tests_properties(onnx-upstream-controls PROPERTIES TIMEOUT 180)
