// Origin: EmberBSD, OpenAI Codex (GPT-6), AI-assisted; not submitted upstream.
// SPDX-License-Identifier: BSD-2-Clause

#include "qserialportinfo_netbsd_p.h"
#include <cstdio>

int main()
{
    int failures = 0;
    for (const char *name : {"dty00", "dty01", "dtyU0", "dtyU123", "dtyY0",
                             "dtyZ1", "dtyC2", "dtyh0", "dtyCY000", "dtyCZ0000", "dtyTX00",
                             "dtyHS0.0", "dtyA00", "dtyS0"}) {
        if (!QT_PREPEND_NAMESPACE(QSerialPortInfoNetBSDPrivate)::isDialoutDeviceName(QString::fromLatin1(name))) {
            std::fprintf(stderr, "missing NetBSD serial family: %s\n", name);
            ++failures;
        }
    }
    for (const char *name : {"null", "uhid0", "ttyU0", "dty", "dtygarbage", "dtyU0.lock",
                             "dtyU-1", "dtyU1/extra", "dtyU1\n", "dtyCY", "dtyCZ", "dtyff"}) {
        if (QT_PREPEND_NAMESPACE(QSerialPortInfoNetBSDPrivate)::isDialoutDeviceName(QString::fromLatin1(name))) {
            std::fprintf(stderr, "accepted unrelated name: %s\n", name);
            ++failures;
        }
    }
    std::printf("device_name_failures=%d\n", failures);
    return failures ? 1 : 0;
}
