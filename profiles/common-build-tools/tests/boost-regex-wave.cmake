# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
cmake_minimum_required(VERSION 3.17)
project(boost_regex_wave_check LANGUAGES CXX)
find_package(Boost CONFIG REQUIRED COMPONENTS regex wave filesystem thread)
add_executable(boost-regex-wave regex-wave.cpp)
target_link_libraries(boost-regex-wave PRIVATE Boost::regex Boost::wave Boost::filesystem Boost::thread)
