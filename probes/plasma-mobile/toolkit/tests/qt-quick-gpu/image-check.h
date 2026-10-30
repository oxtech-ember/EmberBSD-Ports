// SPDX-License-Identifier: BSD-2-Clause
#pragma once
#include "pixel-geometry.h"
#include <QColor>
#include <QImage>

inline bool scenePixelsMatch(const QImage &image, const QColor &expected)
{
    const PixelGeometry sample = sceneSample(image.width(), image.height());
    if (!sample.valid)
        return false;
    for (int y = 0; y < 32; ++y)
        for (int x = 0; x < 32; ++x)
            if (image.pixelColor(sample.x + x, sample.y + y) != expected ||
                image.pixelColor(32 + x, 32 + y) != QColor(Qt::green))
                return false;
    return true;
}
