# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current upstream wrapper around common FreeImage.
cmake_minimum_required(VERSION 3.16)
project(FreeImagePlus VERSION 3.19.25 LANGUAGES CXX)
include(GNUInstallDirs)
find_package(FreeImage 3.19.25 CONFIG REQUIRED)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(wrapper "${FREEIMAGE_SOURCE_ROOT}/Wrapper/FreeImagePlus")
add_library(FreeImagePlusObjects OBJECT
    "${wrapper}/src/FreeImagePlus.cpp" "${wrapper}/src/fipImage.cpp"
    "${wrapper}/src/fipMemoryIO.cpp" "${wrapper}/src/fipMetadataFind.cpp"
    "${wrapper}/src/fipMultiPage.cpp" "${wrapper}/src/fipTag.cpp"
    "${wrapper}/src/fipWinImage.cpp")
set_target_properties(FreeImagePlusObjects PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(FreeImagePlusObjects PRIVATE "${wrapper}")
target_link_libraries(FreeImagePlusObjects PRIVATE FreeImage::FreeImage)
add_library(FreeImagePlus SHARED $<TARGET_OBJECTS:FreeImagePlusObjects>)
add_library(FreeImagePlusStatic STATIC $<TARGET_OBJECTS:FreeImagePlusObjects>)
set_target_properties(FreeImagePlus PROPERTIES OUTPUT_NAME freeimageplus
    VERSION ${PROJECT_VERSION} SOVERSION 3)
set_target_properties(FreeImagePlusStatic PROPERTIES OUTPUT_NAME freeimageplus)
target_link_libraries(FreeImagePlus PUBLIC FreeImage::FreeImage)
target_include_directories(FreeImagePlus PUBLIC "${wrapper}")
install(TARGETS FreeImagePlus FreeImagePlusStatic
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES "${wrapper}/FreeImagePlus.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
enable_testing()
add_executable(FreeImagePlusTest
    "${wrapper}/test/fipTest.cpp" "${wrapper}/test/fipTestMemIO.cpp"
    "${wrapper}/test/fipTestMPage.cpp" "${wrapper}/test/fipTestMPageMemory.cpp"
    "${wrapper}/test/fipTestMPageStream.cpp")
target_link_libraries(FreeImagePlusTest PRIVATE FreeImagePlus)
target_compile_options(FreeImagePlusTest PRIVATE -UNDEBUG)
add_test(NAME FreeImagePlusTest COMMAND FreeImagePlusTest)
set_tests_properties(FreeImagePlusTest PROPERTIES WORKING_DIRECTORY "${wrapper}/test")
