// SPDX-License-Identifier: BSD-2-Clause
#include "image-check.h"
#include <cassert>
#include <initializer_list>

int main()
{
    for (int width : {224, 640, 1920}) {
        for (int height : {128, 400, 1080}) {
            QImage image(width, height, QImage::Format_RGB32);
            image.fill(Qt::red);
            for (int y = 16; y < 80; ++y)
                for (int x = 16; x < 80; ++x)
                    image.setPixelColor(x, y, Qt::green);
            assert(scenePixelsMatch(image, QColor(Qt::red)));
            assert(!scenePixelsMatch(image, QColor(Qt::blue)));
            image.setPixelColor(32, 32, Qt::blue);
            assert(!scenePixelsMatch(image, QColor(Qt::red)));
        }
    }
    QImage tooSmall(223, 400, QImage::Format_RGB32);
    tooSmall.fill(Qt::red);
    assert(!scenePixelsMatch(tooSmall, QColor(Qt::red)));
}
