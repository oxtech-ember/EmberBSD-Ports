#include <rectpack2D/rect_structs.h>
#include <geometry/rtree.h>
#include <tinyspline.h>
#include <tinysplinecxx.h>

int main()
{
    rectpack2D::rect_xywh rectangle(0, 0, 10, 10);
    if (rectangle.w != 10 || rectangle.h != 10)
        return 1;

    RTree<int, int, 2> tree;
    const int minimum[] = {0, 0};
    const int maximum[] = {1, 1};
    tree.Insert(minimum, maximum, 7);
    if (tree.Search(minimum, maximum, [](const int& id) { return id == 7; }) != 1)
        return 2;

    tsBSpline spline;
    if (ts_bspline_new(2, 1, 1, TS_CLAMPED, &spline, nullptr) != TS_SUCCESS)
        return 3;
    ts_bspline_free(&spline);

    tinyspline::BSpline curve(2, 1, 1);
    const std::vector<tinyspline::real> samples = curve.sample(4);
    if (samples.empty())
        return 4;
    return 0;
}
