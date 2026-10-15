// SPDX-License-Identifier: MIT
#ifndef EMBER_OMPL_GEOMETRY_H
#define EMBER_OMPL_GEOMETRY_H
#include <algorithm>
#include <cmath>
#include <limits>
namespace geometry {
struct Point { double x, y; };
struct Rectangle { double left, right, bottom, top; };
inline bool inside(Point p, Rectangle r) {
    return p.x >= r.left && p.x <= r.right && p.y >= r.bottom && p.y <= r.top;
}
inline bool bounded(Point p) {
    return std::isfinite(p.x) && std::isfinite(p.y) &&
        p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1;
}
// Clip the whole closed segment against both rectangle slabs. Touching counts
// as collision; no sampling resolution or OMPL motion checker is consulted.
// Expand the rectangle by a roundoff guard in the unit square so decimal
// corner tangency cannot become a false clearance after division rounding.
inline bool segment_hits_rectangle(Point a, Point b, Rectangle r) {
    double enter = 0, leave = 1;
    constexpr double guard = 32 * std::numeric_limits<double>::epsilon();
    const double origin[] = {a.x, a.y}, end[] = {b.x, b.y};
    const double low[] = {r.left - guard, r.bottom - guard};
    const double high[] = {r.right + guard, r.top + guard};
    for (int dimension = 0; dimension < 2; ++dimension) {
        const double direction = end[dimension] - origin[dimension];
        if (direction == 0) {
            if (origin[dimension] < low[dimension] || origin[dimension] > high[dimension])
                return false;
        } else {
            double near = (low[dimension] - origin[dimension]) / direction;
            double far = (high[dimension] - origin[dimension]) / direction;
            if (near > far) std::swap(near, far);
            enter = std::max(enter, near);
            leave = std::min(leave, far);
            if (enter > leave) return false;
        }
    }
    return true;
}
}
#endif
