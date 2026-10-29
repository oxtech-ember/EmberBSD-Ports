# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
cmake_minimum_required(VERSION 3.24)
project(QtMarkdownConsumer LANGUAGES CXX)
find_package(Qt6 6.12 REQUIRED COMPONENTS Gui)
add_executable(qt-markdown main.cpp)
target_link_libraries(qt-markdown PRIVATE Qt6::Gui)
