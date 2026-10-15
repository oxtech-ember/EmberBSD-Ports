// SPDX-License-Identifier: BSD-2-Clause
// Execute the upstream Waiter with the real Qt private argc contract.
#include "waiter.h"
#include <private/qcoreapplication_p.h>
#include <cstdio>

int main()
{
    int argc = 2;
    char program[] = "plasma_waitforname";
    char service[] = "org.example.WaiterContract";
    char *argv[] = {program, service, nullptr};
    Waiter app(argc, argv);
    const auto *priv = static_cast<const QCoreApplicationPrivate *>(QObjectPrivate::get(&app));
    // Compare addresses before any read of the expired baseline reference.
    if (&priv->argc != &argc) {
        std::fputs("FAIL: QCoreApplication retained constructor-local argc\n", stderr);
        return 1;
    }
    if (QCoreApplication::arguments() != QStringList{QString::fromLatin1(program), QString::fromLatin1(service)})
        return 2;
    if (QCoreApplication::applicationFilePath().isEmpty() || QCoreApplication::applicationDirPath().isEmpty())
        return 3;
    std::puts("PASS: main argc lifetime, arguments and application paths");
    return 0;
}
