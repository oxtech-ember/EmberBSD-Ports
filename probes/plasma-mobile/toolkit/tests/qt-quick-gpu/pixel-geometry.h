// SPDX-License-Identifier: BSD-2-Clause
#pragma once

struct PixelGeometry {
    int x;
    int y;
    bool valid;
};

inline PixelGeometry sceneSample(int width, int height)
{
    // The layer occupies [16, 80) on both axes; leave a gap from it.
    if (width < 224 || height < 128)
        return {0, 0, false};
    return {width / 2 - 16, height / 2 - 16, true};
}
