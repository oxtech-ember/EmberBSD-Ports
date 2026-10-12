# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.24)
project(EmberQtMultimedia LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS Multimedia Gui)
qt_standard_project_setup(REQUIRES 6.12)
qt_add_executable(qt-multimedia main.cpp)
target_link_libraries(qt-multimedia PRIVATE Qt6::Multimedia Qt6::Gui)
target_compile_options(qt-multimedia PRIVATE -Wall -Wextra -Werror)
