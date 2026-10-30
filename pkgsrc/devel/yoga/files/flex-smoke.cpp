// SPDX-License-Identifier: MIT
#include <yoga/Yoga.h>
#include <cmath>
#include <cstdio>

int main()
{
    YGNodeRef root = YGNodeNew();
    YGNodeRef first = YGNodeNew();
    YGNodeRef second = YGNodeNew();
    YGNodeStyleSetWidth(root, 300);
    YGNodeStyleSetHeight(root, 100);
    YGNodeStyleSetFlexDirection(root, YGFlexDirectionRow);
    YGNodeStyleSetWidth(first, 100);
    YGNodeStyleSetFlexGrow(second, 1);
    YGNodeInsertChild(root, first, 0);
    YGNodeInsertChild(root, second, 1);
    YGNodeCalculateLayout(root, YGUndefined, YGUndefined, YGDirectionLTR);
    bool ok = std::fabs(YGNodeLayoutGetWidth(first) - 100) < 0.01f &&
        std::fabs(YGNodeLayoutGetWidth(second) - 200) < 0.01f &&
        std::fabs(YGNodeLayoutGetLeft(second) - 100) < 0.01f;
    YGNodeFreeRecursive(root);
    if (!ok)
        return 1;
    std::puts("Yoga flex layout PASS");
    return 0;
}
