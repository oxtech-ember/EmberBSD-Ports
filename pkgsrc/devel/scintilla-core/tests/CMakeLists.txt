# SPDX-License-Identifier: BSD-2-Clause
cmake_minimum_required(VERSION 3.16)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    project(ScintillaCoreContract LANGUAGES CXX)
    find_package(ScintillaCore 5.6.9 EXACT CONFIG REQUIRED)
    enable_testing()
endif()
# Link real core objects into a DSO: non-PIC archives fail on affected targets.
# These Unicode operations need no GUI/backend implementation or test stubs.
add_library(scintilla-core-pic-contract SHARED core-contract.cpp)
set_target_properties(scintilla-core-pic-contract PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
target_link_libraries(scintilla-core-pic-contract PRIVATE Scintilla::Core)
add_executable(scintilla-core-contract main.cpp)
target_link_libraries(scintilla-core-contract PRIVATE scintilla-core-pic-contract)
add_test(NAME scintilla-core-contract COMMAND scintilla-core-contract)
