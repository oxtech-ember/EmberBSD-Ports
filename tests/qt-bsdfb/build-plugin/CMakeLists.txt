cmake_minimum_required(VERSION 3.22)

set(QT_REPO_MODULE_VERSION 6.12.0)
project(EmberBsdFbPluginCrossBuild VERSION ${QT_REPO_MODULE_VERSION} LANGUAGES C CXX)

if(NOT IS_ABSOLUTE "${QTBASE_SOURCE_DIR}" OR
        NOT EXISTS "${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb/CMakeLists.txt")
    message(FATAL_ERROR "Set QTBASE_SOURCE_DIR to the patched QtBase source tree")
endif()

find_package(Qt6 ${PROJECT_VERSION} EXACT CONFIG REQUIRED COMPONENTS BuildInternals)
qt_internal_project_setup()
find_package(Qt6 ${PROJECT_VERSION} EXACT CONFIG REQUIRED COMPONENTS
    Core Gui FbSupportPrivate)

qt_build_repo_begin()
add_subdirectory("${QTBASE_SOURCE_DIR}/src/plugins/platforms/bsdfb" upstream-bsdfb)
qt_build_repo_end()
