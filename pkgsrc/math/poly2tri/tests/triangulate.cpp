// Copyright (c) 2026 EmberBSD contributors
// SPDX-License-Identifier: BSD-3-Clause
#include <poly2tri/poly2tri.h>

#include <cassert>
#include <stdexcept>
#include <vector>

int main() {
    p2t::Point a(0, 0), b(2, 0), c(0, 2), inner(0.5, 0.5);
    std::vector<p2t::Point*> contour{&a, &b, &c};
    p2t::CDT triangulator(contour);
    triangulator.AddPoint(&inner);
    bool rejected = false;
    try {
        triangulator.AddPoint(&inner);
    } catch (const std::runtime_error&) {
        rejected = true;
    }
    assert(rejected);
    triangulator.Triangulate();
    assert(triangulator.GetTriangles().size() == 3);
}
