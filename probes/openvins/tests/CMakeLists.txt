# SPDX-License-Identifier: MIT
cmake_minimum_required(VERSION 3.20)
project(openvins_installed_contract LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Eigen3 5.0.1 EXACT REQUIRED CONFIG PATHS "${EIGEN_PREFIX}/share/eigen3/cmake" NO_DEFAULT_PATH)
find_package(OpenCV 5.0.0 EXACT REQUIRED COMPONENTS core imgproc imgcodecs features calib geometry video
    PATHS "${OPENCV_PREFIX}/lib/cmake/opencv5" NO_DEFAULT_PATH)
find_package(Ceres 2.2.0 EXACT REQUIRED CONFIG PATHS "${CERES_PREFIX}/lib/cmake/Ceres" NO_DEFAULT_PATH)
find_package(Boost 1.92.0 EXACT REQUIRED COMPONENTS filesystem thread date_time)
find_library(OPENVINS_LIBRARY ov_msckf_lib PATHS "${PROBE_PREFIX}/lib" NO_DEFAULT_PATH REQUIRED)
add_executable(openvins-contract contract.cpp)
target_include_directories(openvins-contract PRIVATE "${PROBE_PREFIX}/include/open_vins" ${OpenCV_INCLUDE_DIRS})
target_compile_definitions(openvins-contract PRIVATE ROS_AVAILABLE=0 ENABLE_ARUCO_TAGS=0 HAVE_PYTHONLIBS=0)
target_link_libraries(openvins-contract PRIVATE "${OPENVINS_LIBRARY}" Eigen3::Eigen Ceres::ceres
    Boost::filesystem Boost::thread Boost::date_time ${OpenCV_LIBS})
enable_testing()
add_test(NAME independent-vio-trajectory COMMAND openvins-contract)
set_tests_properties(independent-vio-trajectory PROPERTIES TIMEOUT 180)
# The cross flow installs the built consumer into the accept directory.
install(TARGETS openvins-contract DESTINATION .)
