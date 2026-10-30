// SPDX-License-Identifier: BSD-2-Clause
#include "pixel-geometry.h"
#include <cassert>
#include <initializer_list>

int main()
{
    for (int width : {224, 640, 1920}) {
        for (int height : {128, 400, 1080}) {
            const auto sample = sceneSample(width, height);
            assert(sample.valid && sample.x >= 80 && sample.x + 31 < width);
            assert(sample.y >= 0 && sample.y + 31 < height);
        }
    }
    assert(!sceneSample(223, 400).valid);
    assert(!sceneSample(640, 127).valid);
}
