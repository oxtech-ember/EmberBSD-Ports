# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.24)
project(EmberQtSpeech LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS TextToSpeech Multimedia)
qt_standard_project_setup(REQUIRES 6.12)
qt_add_executable(qt-speech main.cpp)
target_link_libraries(qt-speech PRIVATE Qt6::TextToSpeech Qt6::Multimedia)
target_compile_options(qt-speech PRIVATE -Wall -Wextra -Werror)
