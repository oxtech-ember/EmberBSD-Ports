# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.24)
project(EmberQtWaylandGL LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS Core Gui OpenGL)
qt_standard_project_setup(REQUIRES 6.12)
qt_add_executable(qt-wayland-gl main.cpp)
target_link_libraries(qt-wayland-gl PRIVATE Qt6::Core Qt6::Gui Qt6::OpenGL)
target_compile_options(qt-wayland-gl PRIVATE -Wall -Wextra -Werror)
