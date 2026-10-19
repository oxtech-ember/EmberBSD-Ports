cmake_minimum_required(VERSION 3.16)
project(fmtlib_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(fmt CONFIG REQUIRED)

add_executable(fmtlib-contract formatting.cc)
target_link_libraries(fmtlib-contract PRIVATE fmt::fmt)
