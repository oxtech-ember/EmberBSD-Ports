// SPDX-License-Identifier: MIT
#include "geometry.h"
#include <ompl/base/ScopedState.h>
#include <ompl/base/spaces/RealVectorStateSpace.h>
#include <ompl/base/terminationconditions/IterationTerminationCondition.h>
#include <ompl/geometric/SimpleSetup.h>
#include <ompl/geometric/planners/rrt/RRTConnect.h>
#include <ompl/util/RandomNumbers.h>
#include <ompl/config.h>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>
namespace ob = ompl::base;
namespace og = ompl::geometric;
using geometry::Point;
using geometry::Rectangle;
static void require(bool value, const char *message) {
    if (!value) throw std::runtime_error(message);
}
static Point point(const ob::State *state) {
    const auto *value = state->as<ob::RealVectorStateSpace::StateType>();
    return {value->values[0], value->values[1]};
}
static void validate_path(const og::PathGeometric &path, Rectangle obstacle,
                          bool exact) {
    require(path.getStateCount() >= 2, "Path has fewer than two states");
    const auto first = point(path.getState(0));
    const auto last = point(path.getState(path.getStateCount() - 1));
    require(std::hypot(first.x - .1, first.y - .5) < 1e-8, "Path missed start");
    if (exact)
        require(std::hypot(last.x - .9, last.y - .5) < 1e-8, "Path missed goal");
    double length = 0;
    for (std::size_t i = 0; i < path.getStateCount(); ++i) {
        const Point current = point(path.getState(i));
        require(geometry::bounded(current) && !geometry::inside(current, obstacle),
                "A path state is out of bounds or inside the obstacle");
        if (i) {
            const Point previous = point(path.getState(i - 1));
            require(!geometry::segment_hits_rectangle(previous, current, obstacle),
                    "Continuous segment intersects the closed obstacle");
            length += std::hypot(current.x - previous.x, current.y - previous.y);
        }
    }
    require(std::isfinite(length) && std::abs(length - path.length()) < 1e-8,
            "Path length differs from independent calculation");
    if (exact) require(length > .8 && length < 5, "Unexpected detour length");
    std::printf("states=%zu length=%.12f\n", path.getStateCount(), length);
}
int main(int argc, char **argv) {
    try {
        require(argc == 2, "Usage: ompl-contract path|invalid-goal|blocked");
        require(OMPL_MAJOR_VERSION == 2 && OMPL_MINOR_VERSION == 0 &&
                OMPL_PATCH_VERSION == 2, "Unexpected installed OMPL version");
        ompl::RNG::setSeed(104729);
        const std::string mode = argv[1];
        const bool blocked = mode == "blocked";
        require(blocked || mode == "path" || mode == "invalid-goal", "Unknown mode");
        const Rectangle obstacle = blocked ? Rectangle{.45, .55, 0, 1} :
                                              Rectangle{.4, .6, .15, .85};
        auto space = std::make_shared<ob::RealVectorStateSpace>(2);
        ob::RealVectorBounds bounds(2);
        bounds.setLow(0); bounds.setHigh(1); space->setBounds(bounds);
        og::SimpleSetup setup(space);
        setup.setStateValidityChecker([obstacle](const ob::State *state) {
            const Point p = point(state);
            return geometry::bounded(p) && !geometry::inside(p, obstacle);
        });
        // OMPL checks sampled states along each edge. The independent final
        // validator above checks the entire continuous segment analytically.
        setup.getSpaceInformation()->setStateValidityCheckingResolution(.0005);
        ob::ScopedState<> start(space), goal(space);
        start[0] = .1; start[1] = .5;
        goal[0] = mode == "invalid-goal" ? .5 : .9; goal[1] = .5;
        setup.setStartAndGoalStates(start, goal, 1e-9);
        auto planner = std::make_shared<og::RRTConnect>(setup.getSpaceInformation());
        planner->setRange(.07);
        setup.setPlanner(planner);
        ob::IterationTerminationCondition iterations(mode == "invalid-goal" ? 256 :
                                                      blocked ? 4000 : 20000);
        const auto result = setup.solve(iterations);
        if (mode == "path") {
            require(result == ob::PlannerStatus::EXACT_SOLUTION &&
                    setup.haveExactSolutionPath(), "No exact bounded-budget path");
            validate_path(setup.getSolutionPath(), obstacle, true);
        } else if (mode == "invalid-goal") {
            require(result == ob::PlannerStatus::INVALID_GOAL &&
                    !setup.haveSolutionPath(), "Goal inside obstacle was accepted");
        } else {
            require(!setup.haveExactSolutionPath() &&
                    (result == ob::PlannerStatus::TIMEOUT ||
                     result == ob::PlannerStatus::APPROXIMATE_SOLUTION),
                    "Planner claimed a path through a separating wall");
            if (setup.haveSolutionPath()) validate_path(setup.getSolutionPath(), obstacle, false);
        }
        std::printf("%s: PASS (seed=104729, status=%s)\n", argv[1], result.asString().c_str());
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
}
