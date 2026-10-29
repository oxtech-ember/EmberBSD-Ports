# SPDX-License-Identifier: BSD-2-Clause
cmake_minimum_required(VERSION 3.16)
project(qtexr LANGUAGES CXX)
find_package(Qt6 6.12 REQUIRED COMPONENTS Core Quick3DRuntimeRender Quick3DRuntimeRenderPrivate)
add_executable(qtexr main.cpp)
target_link_libraries(qtexr PRIVATE Qt6::Quick3DRuntimeRenderPrivate Qt6::Core)
