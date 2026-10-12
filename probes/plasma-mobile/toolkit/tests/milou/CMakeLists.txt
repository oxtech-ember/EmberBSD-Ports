# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.24)
project(EmberMilouMime LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS Core Gui Qml)
qt_standard_project_setup(REQUIRES 6.12)
qt_add_executable(milou-mime mime.cpp)
target_link_libraries(milou-mime PRIVATE Qt6::Core Qt6::Gui Qt6::Qml)
target_compile_options(milou-mime PRIVATE -Wall -Wextra -Werror)
