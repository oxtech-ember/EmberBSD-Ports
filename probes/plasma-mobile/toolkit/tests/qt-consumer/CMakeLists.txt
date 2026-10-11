# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.24)
project(EmberQtConsumer LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS Core Gui Svg)
qt_standard_project_setup(REQUIRES 6.12)
qt_add_executable(qt-consumer main.cpp)
qt_add_resources(qt-consumer "fixture"
    PREFIX "/ember-check"
    FILES fixture.svg
)
target_link_libraries(qt-consumer PRIVATE Qt6::Core Qt6::Gui Qt6::Svg)
target_compile_options(qt-consumer PRIVATE -Wall -Wextra -Werror)
