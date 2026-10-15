# SPDX-License-Identifier: MIT
# Included by CMAKE_PROJECT_ompl_INCLUDE after project() enables C++.
find_package(Eigen3 5.0.1 EXACT CONFIG REQUIRED
    PATHS "${EIGEN_PREFIX}/share/eigen3/cmake" NO_DEFAULT_PATH)
set(Boost_DIR "${BOOST_PREFIX}/lib/cmake/Boost-1.92.0" CACHE PATH "Selected common Boost")
find_package(Boost 1.92.0 EXACT CONFIG REQUIRED COMPONENTS serialization program_options unit_test_framework)
