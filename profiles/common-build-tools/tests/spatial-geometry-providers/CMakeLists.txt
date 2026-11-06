cmake_minimum_required(VERSION 3.23)
project(spatial_geometry_providers LANGUAGES C CXX)

find_package(rectpack2d CONFIG REQUIRED)
find_package(rtree CONFIG REQUIRED)
find_package(tinyspline CONFIG REQUIRED)
find_package(tinysplinecxx CONFIG REQUIRED)

add_executable(spatial-geometry-providers main.cpp)
target_link_libraries(spatial-geometry-providers PRIVATE
  rectpack2d::rectpack2d
  rtree::rtree
  tinyspline::tinyspline
  tinysplinecxx::tinysplinecxx)
