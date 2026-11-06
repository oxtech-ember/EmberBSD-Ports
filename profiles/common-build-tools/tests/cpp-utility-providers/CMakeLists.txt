cmake_minimum_required(VERSION 3.23)
project(cpp_utility_providers LANGUAGES C CXX)

find_package(nanoflann CONFIG REQUIRED)
find_package(parson CONFIG REQUIRED)
find_package(rapidcsv CONFIG REQUIRED)
find_path(PICOSHA2_INCLUDE_DIR NAMES picosha2.h REQUIRED)

add_executable(cpp-utility-providers main.cpp)
target_include_directories(cpp-utility-providers PRIVATE "${PICOSHA2_INCLUDE_DIR}")
target_link_libraries(cpp-utility-providers PRIVATE
  nanoflann::nanoflann
  parson::parson
  rapidcsv::rapidcsv)
