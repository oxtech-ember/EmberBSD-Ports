cmake_minimum_required(VERSION 3.22)
# Origin: EmberBSD contributors (AI-assisted).
set(QT_REPO_MODULE_VERSION 6.12.0)
project(EmberVncPluginControl VERSION ${QT_REPO_MODULE_VERSION} LANGUAGES C CXX)

if(NOT IS_ABSOLUTE "${QTBASE_SOURCE_DIR}" OR
        NOT EXISTS "${QTBASE_SOURCE_DIR}/src/plugins/platforms/vnc/CMakeLists.txt")
    message(FATAL_ERROR "Set QTBASE_SOURCE_DIR to the matching real QtBase source tree")
endif()

find_package(Qt6 ${PROJECT_VERSION} EXACT CONFIG REQUIRED COMPONENTS BuildInternals)
qt_internal_project_setup()
find_package(Qt6 ${PROJECT_VERSION} EXACT CONFIG REQUIRED COMPONENTS
    Core Gui Network FbSupportPrivate InputSupportPrivate)

qt_build_repo_begin()
add_subdirectory("${QTBASE_SOURCE_DIR}/src/plugins/platforms/vnc" upstream-vnc)
qt_build_repo_end()
