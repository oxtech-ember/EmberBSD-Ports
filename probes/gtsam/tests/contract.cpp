// SPDX-License-Identifier: MIT
#include <gtsam/geometry/Pose2.h>
#include <gtsam/linear/GaussianFactorGraph.h>
#include <gtsam/linear/JacobianFactor.h>
#include <gtsam/linear/linearExceptions.h>
#include <gtsam/nonlinear/LevenbergMarquardtOptimizer.h>
#include <gtsam/nonlinear/Marginals.h>
#include <gtsam/slam/BetweenFactor.h>
#include <gtsam/slam/PriorFactor.h>
#include "matrix-check.h"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

static void require(bool value, const char* message)
{
    if (!value) throw std::runtime_error(message);
}

static void linear_fusion(bool underconstrained)
{
    using namespace gtsam;
    GaussianFactorGraph graph;
    const Matrix A = Matrix::Identity(1, 1);
    const auto noise = noiseModel::Isotropic::Sigma(1, 1.0);
    // Equal-variance measurements: x0=0, x1-x0=2, x1=3.
    // Analytic solution of [[2,-1],[-1,2]] x = [-2,5] is [1/3,8/3].
    graph.emplace_shared<JacobianFactor>(0, -A, 1, A, Vector1(2.0), noise);
    if (underconstrained) {
        bool caught = false;
        try { (void)graph.optimize(); }
        catch (const IndeterminateSystemException&) { caught = true; }
        require(caught, "unanchored state did not report indeterminacy");
        return;
    }
    graph.emplace_shared<JacobianFactor>(0, A, Vector1(0.0), noise);
    graph.emplace_shared<JacobianFactor>(1, A, Vector1(3.0), noise);
    const VectorValues result = graph.optimize();
    require(std::abs(result.at(0)(0) - 1.0 / 3.0) < 1e-10, "fused initial state");
    require(std::abs(result.at(1)(0) - 8.0 / 3.0) < 1e-10, "fused final state");
    require(std::abs(graph.error(result) - 1.0 / 6.0) < 1e-10, "fusion residual cost");
}

static void pose_graph(bool missing_state)
{
    using namespace gtsam;
    const double pi = std::acos(-1.0);
    const auto noise = noiseModel::Isotropic::Sigma(3, 0.1);
    NonlinearFactorGraph graph;
    graph.emplace_shared<PriorFactor<Pose2>>(0, Pose2(0, 0, 0), noise);
    graph.emplace_shared<BetweenFactor<Pose2>>(0, 1, Pose2(2, 0, 0), noise);
    graph.emplace_shared<BetweenFactor<Pose2>>(1, 2, Pose2(0, 2, pi / 2), noise);
    graph.emplace_shared<BetweenFactor<Pose2>>(0, 2, Pose2(2, 2, pi / 2), noise);
    Values initial;
    initial.insert(0, Pose2(0.1, -0.2, 0.03));
    initial.insert(1, Pose2(2.2, 0.1, -0.04));
    if (missing_state) {
        bool caught = false;
        try { (void)graph.error(initial); }
        catch (const ValuesKeyDoesNotExist&) { caught = true; }
        require(caught, "missing pose was not rejected");
        return;
    }
    initial.insert(2, Pose2(1.9, 2.2, pi / 2 + 0.05));
    const double before = graph.error(initial);
    LevenbergMarquardtParams params;
    params.setMaxIterations(100);
    params.setRelativeErrorTol(1e-12);
    params.setAbsoluteErrorTol(1e-12);
    const Values result = LevenbergMarquardtOptimizer(graph, initial, params).optimize();
    const Pose2 expected[] = {Pose2(0, 0, 0), Pose2(2, 0, 0), Pose2(2, 2, pi / 2)};
    for (Key i = 0; i < 3; ++i) {
        const auto actual = result.at<Pose2>(i);
        require(std::abs(actual.x() - expected[i].x()) < 1e-7, "pose x");
        require(std::abs(actual.y() - expected[i].y()) < 1e-7, "pose y");
        require(std::abs(actual.theta() - expected[i].theta()) < 1e-7, "pose angle");
    }
    require(before > 1.0 && graph.error(result) < 1e-12, "pose graph cost reduction");
    // The anchor has covariance sigma^2 I: only relative measurements follow it.
    const Matrix covariance = Marginals(graph, result).marginalCovariance(0);
    require(finite_matrix_near(covariance, Matrix::Identity(3, 3) * 0.01, 1e-8),
        "anchor covariance differs from prior");
}

int main(int argc, char** argv)
{
    try {
        require(EIGEN_MAJOR_VERSION == 5 && EIGEN_MINOR_VERSION == 0 &&
            EIGEN_PATCH_VERSION == 1, "wrong Eigen headers");
        require(argc == 2, "expected one case");
        const std::string test = argv[1];
        if (test == "linear-fusion") linear_fusion(false);
        else if (test == "underconstrained") linear_fusion(true);
        else if (test == "pose-graph") pose_graph(false);
        else if (test == "missing-state") pose_graph(true);
        else throw std::runtime_error("unknown case");
        std::cout << "PASS " << test << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}
