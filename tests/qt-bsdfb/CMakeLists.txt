cmake_minimum_required(VERSION 3.22)
project(ember_qt_bsdfb_layout_tests LANGUAGES CXX)

set(QTBASE_SOURCE_DIR "" CACHE PATH "QtBase source tree containing the bsdfb helper")
if(NOT QTBASE_SOURCE_DIR)
    message(FATAL_ERROR "Set QTBASE_SOURCE_DIR to the QtBase source tree")
endif()

add_executable(qt-bsdfb-layout-test layout.cpp)
target_include_directories(qt-bsdfb-layout-test PRIVATE
    "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb")
target_compile_features(qt-bsdfb-layout-test PRIVATE cxx_std_17)
set_target_properties(qt-bsdfb-layout-test PROPERTIES
    CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
target_compile_options(qt-bsdfb-layout-test PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)

enable_testing()
add_test(NAME qt-bsdfb-layout COMMAND qt-bsdfb-layout-test)

add_executable(qt-bsdfb-pointer-test pointer.cpp)
target_include_directories(qt-bsdfb-pointer-test PRIVATE
    "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb")
target_compile_features(qt-bsdfb-pointer-test PRIVATE cxx_std_17)
set_target_properties(qt-bsdfb-pointer-test PROPERTIES
    CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
target_compile_options(qt-bsdfb-pointer-test PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
add_test(NAME qt-bsdfb-pointer COMMAND qt-bsdfb-pointer-test)

add_executable(qt-bsdfb-recordbuffer-test records.cpp)
target_include_directories(qt-bsdfb-recordbuffer-test PRIVATE
    "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb")
target_compile_features(qt-bsdfb-recordbuffer-test PRIVATE cxx_std_17)
set_target_properties(qt-bsdfb-recordbuffer-test PROPERTIES
    CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
target_compile_options(qt-bsdfb-recordbuffer-test PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
add_test(NAME qt-bsdfb-recordbuffer COMMAND qt-bsdfb-recordbuffer-test)

set(QT_HOST_PREFIX "" CACHE PATH "Optional Qt 6.12 host prefix for FrameGate test")
if(QT_HOST_PREFIX)
    if(NOT IS_ABSOLUTE "${QT_HOST_PREFIX}")
        message(FATAL_ERROR "QT_HOST_PREFIX must be an absolute Qt 6.12 host prefix")
    endif()
    find_package(Qt6 6.12.0 EXACT CONFIG REQUIRED COMPONENTS Core Gui
        PATHS "${QT_HOST_PREFIX}/lib/cmake" NO_DEFAULT_PATH)

    add_executable(qt-bsdfb-framegate-test framegate.cpp)
    target_include_directories(qt-bsdfb-framegate-test PRIVATE
        "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb")
    target_compile_features(qt-bsdfb-framegate-test PRIVATE cxx_std_17)
    set_target_properties(qt-bsdfb-framegate-test PROPERTIES
        CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
    target_compile_options(qt-bsdfb-framegate-test PRIVATE
        -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(qt-bsdfb-framegate-test PRIVATE -stdlib=libstdc++)
        target_link_options(qt-bsdfb-framegate-test PRIVATE -stdlib=libstdc++)
    endif()
    target_link_libraries(qt-bsdfb-framegate-test PRIVATE Qt6::Core Qt6::Gui)
    add_test(NAME qt-bsdfb-framegate COMMAND qt-bsdfb-framegate-test)

    add_executable(qt-bsdfb-blit-test blit.cpp)
    target_include_directories(qt-bsdfb-blit-test PRIVATE
        "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb")
    target_compile_features(qt-bsdfb-blit-test PRIVATE cxx_std_17)
    set_target_properties(qt-bsdfb-blit-test PROPERTIES
        CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
    target_compile_options(qt-bsdfb-blit-test PRIVATE
        -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(qt-bsdfb-blit-test PRIVATE -stdlib=libstdc++)
        target_link_options(qt-bsdfb-blit-test PRIVATE -stdlib=libstdc++)
    endif()
    target_link_libraries(qt-bsdfb-blit-test PRIVATE Qt6::Core Qt6::Gui)
    add_test(NAME qt-bsdfb-blit COMMAND qt-bsdfb-blit-test)

    add_executable(qt-bsdfb-inputfailure-test inputfailure.cpp)
    target_include_directories(qt-bsdfb-inputfailure-test PRIVATE
        "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb")
    target_compile_features(qt-bsdfb-inputfailure-test PRIVATE cxx_std_17)
    set_target_properties(qt-bsdfb-inputfailure-test PROPERTIES
        CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
    target_compile_options(qt-bsdfb-inputfailure-test PRIVATE
        -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Werror)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(qt-bsdfb-inputfailure-test PRIVATE -stdlib=libstdc++)
        target_link_options(qt-bsdfb-inputfailure-test PRIVATE -stdlib=libstdc++)
    endif()
    target_link_libraries(qt-bsdfb-inputfailure-test PRIVATE Qt6::Core)
    add_test(NAME qt-bsdfb-inputfailure-failure COMMAND qt-bsdfb-inputfailure-test failure)
    add_test(NAME qt-bsdfb-inputfailure-normal COMMAND qt-bsdfb-inputfailure-test normal)
endif()
