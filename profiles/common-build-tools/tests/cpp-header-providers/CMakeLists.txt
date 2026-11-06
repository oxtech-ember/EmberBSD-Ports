cmake_minimum_required(VERSION 3.23)
project(cpp_header_providers LANGUAGES CXX)

find_package(argparse CONFIG REQUIRED)
find_package(sul-dynamic_bitset CONFIG REQUIRED)
find_package(LibPopcnt CONFIG REQUIRED)
find_package(magic_enum CONFIG REQUIRED)
find_package(BS_thread_pool CONFIG REQUIRED)

get_target_property(thread_pool_links BS::thread_pool INTERFACE_LINK_LIBRARIES)
if(NOT "Threads::Threads" IN_LIST thread_pool_links)
  message(FATAL_ERROR "BS::thread_pool must export Threads::Threads")
endif()

add_executable(cpp-header-providers main.cpp)
target_link_libraries(cpp-header-providers PRIVATE
  argparse::argparse
  sul::dynamic_bitset
  LibPopcnt::libpopcnt
  magic_enum::magic_enum
  BS::thread_pool)
