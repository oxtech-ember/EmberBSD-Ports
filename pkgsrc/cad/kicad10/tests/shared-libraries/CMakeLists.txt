cmake_minimum_required(VERSION 3.20)
project(kicad_shared_libraries_consumer LANGUAGES CXX)
find_package(argparse 3.2 CONFIG REQUIRED)
find_package(sul-dynamic_bitset 1.3.3 CONFIG REQUIRED)

find_package(Clipper2 2.0.1 CONFIG REQUIRED)
find_package(FastFloat 8.3.2 CONFIG REQUIRED)
find_package(fmt 12.2.0 CONFIG REQUIRED)
find_package(nlohmann_json 3.12.0 CONFIG REQUIRED)
find_package(NanoSVG 20261029 CONFIG REQUIRED)
find_package(nanodbc 3.0.8 CONFIG REQUIRED)
find_package(tl-expected 1.3.1 CONFIG REQUIRED)
find_package(pybind11 3.1.0 CONFIG REQUIRED)

add_executable(kicad_shared_libraries_consumer main.cpp)
target_compile_features(kicad_shared_libraries_consumer PRIVATE cxx_std_17)
target_link_libraries(kicad_shared_libraries_consumer PRIVATE
    argparse::argparse
    sul::dynamic_bitset
    Clipper2::Clipper2Z
    FastFloat::fast_float
    fmt::fmt
    nlohmann_json::nlohmann_json
    NanoSVG::nanosvg
    nanodbc::nanodbc
    tl::expected
    pybind11::embed
)
