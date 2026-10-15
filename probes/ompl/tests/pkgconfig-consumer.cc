// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise public inline archive dependencies.
#include <ompl/base/ScopedState.h>
#include <ompl/base/StateStorage.h>
#include <ompl/base/spaces/RealVectorStateSpace.h>
#include <cmath>
#include <cstdio>
#include <memory>
#include <sstream>

int main()
{
    namespace ob = ompl::base;
    auto space = std::make_shared<ob::RealVectorStateSpace>(2);
    ob::RealVectorBounds bounds(2);
    bounds.setLow(-1);
    bounds.setHigh(1);
    space->setBounds(bounds);
    space->setup();
    ob::ScopedState<> state(space);
    state[0] = .25;
    state[1] = -.5;
    ob::StateStorageWithMetadata<int> source(space), loaded(space);
    source.addState(state.get(), 42);
    std::stringstream archive(std::ios::in | std::ios::out | std::ios::binary);
    source.store(archive);
    if (!archive.good())
        return 1;
    archive.seekg(0);
    loaded.load(archive);
    if (loaded.size() != 1 || loaded.getMetadata(0) != 42)
        return 1;
    const auto *result = loaded.getState(0)->as<ob::RealVectorStateSpace::StateType>();
    if (std::abs(result->values[0] - .25) > 1e-12 ||
        std::abs(result->values[1] + .5) > 1e-12)
        return 1;
    std::puts("Installed pkg-config consumer: state and inline metadata archive roundtrip PASS");
}
