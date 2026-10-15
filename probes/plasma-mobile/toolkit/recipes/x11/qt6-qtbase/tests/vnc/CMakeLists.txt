cmake_minimum_required(VERSION 3.22)
project(ember_qt_vnc_lifecycle LANGUAGES CXX)
find_package(Qt6 6.12 REQUIRED COMPONENTS Gui)
add_executable(qt-vnc-lifecycle runtime.cpp)
set_target_properties(qt-vnc-lifecycle PROPERTIES
    CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
target_compile_options(qt-vnc-lifecycle PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
target_link_libraries(qt-vnc-lifecycle PRIVATE Qt6::Gui)
