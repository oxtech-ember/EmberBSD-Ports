// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Use real generated KConfig code and storage.
#include "settings.h"
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    if (args.size() != 3 || (args.at(1) != "read" && args.at(1) != "write"))
        return 2;
    bool ok = false;
    const int value = args.at(2).toInt(&ok);
    if (!ok)
        return 2;
    Settings settings;
    if (args.at(1) == "write") {
        settings.setValue(value);
        if (!settings.save())
            return 4;
    } else if (settings.value() != value) {
        std::fprintf(stderr, "Value mismatch: got %d, expected %d\n", settings.value(), value);
        return 3;
    }
    std::puts("PASS: generated KConfig consumer");
    return 0;
}
