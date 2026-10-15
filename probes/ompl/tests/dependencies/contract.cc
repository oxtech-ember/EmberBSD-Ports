// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), numerical and shared-library contracts.
#include <Eigen/Dense>
#include <Eigen/SparseCholesky>
#include <Eigen/Version>
#include <boost/archive/text_iarchive.hpp>
#include <boost/archive/text_oarchive.hpp>
#include <boost/program_options.hpp>
#include <boost/serialization/vector.hpp>
#include <boost/version.hpp>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static void require(bool condition, const char *message)
{
    if (!condition)
        throw std::runtime_error(message);
}

static void numerical_contract()
{
    Eigen::Matrix3d matrix;
    matrix << 4.0, 1.0, 0.0, 1.0, 3.0, 1.0, 0.0, 1.0, 2.0;
    const Eigen::Vector3d expected(0.125, -0.5, 1.75);
    const Eigen::Vector3d rhs = matrix * expected;
    const Eigen::Vector3d dense = matrix.ldlt().solve(rhs);
    require(dense.allFinite() && (dense - expected).norm() < 1e-12 &&
                (matrix * dense - rhs).norm() < 1e-12,
            "Eigen dense solve or residual failed");
    const Eigen::SparseMatrix<double> sparse = matrix.sparseView();
    Eigen::SimplicialLDLT<Eigen::SparseMatrix<double>> solver(sparse);
    require(solver.info() == Eigen::Success, "Eigen sparse factorization failed");
    const Eigen::Vector3d result = solver.solve(rhs);
    require(solver.info() == Eigen::Success && result.allFinite() &&
                (result - expected).norm() < 1e-12 &&
                (sparse * result - rhs).norm() < 1e-12,
            "Eigen sparse solve or residual failed");
}

static void serialization_contract()
{
    const std::vector<double> state{0.125, -0.5, 1.75, 0.0, -1024.25};
    std::stringstream stream;
    {
        boost::archive::text_oarchive archive(stream);
        archive << state;
    }
    require(!stream.str().empty(), "Boost archive is empty");
    std::vector<double> restored;
    {
        boost::archive::text_iarchive archive(stream);
        archive >> restored;
    }
    require(restored == state, "Boost state-vector roundtrip failed");
}

static void options_contract()
{
    namespace po = boost::program_options;
    po::options_description description("Planning input");
    description.add_options()
        ("step", po::value<double>()->required(), "Positive planning step")
        ("name", po::value<std::string>()->required(), "State name");
    const char *valid[]{"contract", "--step", "0.125", "--name", "waypoint"};
    po::variables_map parsed;
    po::store(po::parse_command_line(5, valid, description), parsed);
    po::notify(parsed);
    require(parsed["step"].as<double>() == 0.125 &&
                parsed["name"].as<std::string>() == "waypoint",
            "Boost option values changed");

    const char *missing[]{"contract", "--step", "0.125"};
    bool required_rejected = false;
    try {
        po::variables_map input;
        po::store(po::parse_command_line(3, missing, description), input);
        po::notify(input);
    } catch (const po::required_option &) {
        required_rejected = true;
    }
    require(required_rejected, "Boost accepted a missing required option");

    const char *invalid[]{"contract", "--step", "not-a-number", "--name", "waypoint"};
    bool invalid_rejected = false;
    try {
        po::variables_map input;
        po::store(po::parse_command_line(5, invalid, description), input);
        po::notify(input);
    } catch (const po::invalid_option_value &) {
        invalid_rejected = true;
    }
    require(invalid_rejected, "Boost accepted an invalid double option");
}

int main()
{
    static_assert(EIGEN_MAJOR_VERSION == 5 && EIGEN_MINOR_VERSION == 0 &&
                      EIGEN_PATCH_VERSION == 1,
                  "Eigen 5.0.1 required");
    static_assert(BOOST_VERSION == 109200, "Boost 1.92.0 required");
    try {
        numerical_contract();
        serialization_contract();
        options_contract();
        std::cout << "PASS Eigen 5.0.1 dense/sparse residuals; Boost 1.92.0 "
                     "state-vector serialization, parsed options and shared-library exceptions\n";
    } catch (const std::exception &error) {
        std::cerr << "FAIL common dependencies: " << error.what() << '\n';
        return 1;
    }
}
