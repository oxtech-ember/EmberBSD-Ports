// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include "qbsdfbpresent_p.h"
#include <array>
#include <cstdlib>
#include <iostream>

int main()
{
    int failures = 0;
    const auto check = [&](bool ok) { if (!ok) ++failures; };
    for (const auto format : {QImage::Format_RGB32, QImage::Format_RGBX8888}) {
        std::array<unsigned char, 80> targetBytes;
        targetBytes.fill(0xa5);
        QImage target(targetBytes.data() + 8, 3, 3, 20, format);
        QImage source(3, 3, format);
        source.fill(0xff123456);
        check(QBsdFb::presentImage(target, source, QBsdFb::Rotation::R0));
        for (int y = 0; y < 3; ++y) {
            for (int x = 0; x < 3; ++x)
                check(target.pixel(x, y) == source.pixel(x, y));
            for (std::size_t i = 12; i < 20; ++i)
                check(targetBytes[8 + static_cast<std::size_t>(y) * 20 + i] == 0xa5);
        }
        for (std::size_t i = 0; i < 8; ++i)
            check(targetBytes[i] == 0xa5 && targetBytes[68 + i] == 0xa5);
        const auto before = targetBytes;
        check(!QBsdFb::presentImage(target, QImage(2, 3, format), QBsdFb::Rotation::R0));
        check(!QBsdFb::presentImage(target, QImage(3, 3, QImage::Format_ARGB32), QBsdFb::Rotation::R0));
        check(!QBsdFb::presentImage(target, source, QBsdFb::Rotation::R90));
        check(!QBsdFb::presentImage(target, QImage(), QBsdFb::Rotation::R0));
        check(before == targetBytes);
    }
    if (failures)
        std::cerr << failures << " direct presentation checks failed\n";
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
