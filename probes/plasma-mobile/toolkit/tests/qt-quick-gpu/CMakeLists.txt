# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.24)
project(EmberQtQuickGPU LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS Quick)
qt_standard_project_setup(REQUIRES 6.12)
qt_add_executable(qt-quick-gpu main.cpp)
qt_add_qml_module(qt-quick-gpu
    URI Ember.GpuCheck
    OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/Ember/GpuCheck"
    QML_FILES Scene.qml
)
target_link_libraries(qt-quick-gpu PRIVATE Qt6::Quick)
target_compile_options(qt-quick-gpu PRIVATE -Wall -Wextra -Werror)
