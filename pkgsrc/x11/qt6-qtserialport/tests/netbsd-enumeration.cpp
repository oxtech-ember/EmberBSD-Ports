// Origin: EmberBSD, OpenAI Codex (GPT-6), AI-assisted; not submitted upstream.
// SPDX-License-Identifier: BSD-2-Clause

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QSerialPortInfo>
#include <cstdio>
#include <sys/stat.h>

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    const QString expected = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QString();
    QStringList absent;
    for (int i = 6; i < argc; ++i)
        absent.append(QString::fromLocal8Bit(argv[i]));
    bool found = expected.isEmpty();
    int failures = 0;
    QElapsedTimer elapsed;
    elapsed.start();
    const auto ports = QSerialPortInfo::availablePorts();
    for (const auto &port : ports) {
        const QByteArray path = port.systemLocation().toLocal8Bit();
        if (absent.contains(port.systemLocation())) {
            std::fprintf(stderr, "detached serial device: %s\n", path.constData());
            ++failures;
        }
        struct stat info;
        if (::stat(path.constData(), &info) != 0 || !S_ISCHR(info.st_mode)) {
            std::fprintf(stderr, "not a character device: %s\n", path.constData());
            ++failures;
        }
        if (port.systemLocation() == QStringLiteral("/dev/null")
                || port.systemLocation().startsWith(QStringLiteral("/dev/uhid"))
                || port.systemLocation().startsWith(QStringLiteral("/dev/audio"))) {
            std::fprintf(stderr, "unrelated device: %s\n", path.constData());
            ++failures;
        }
        if (port.systemLocation() == expected) {
            found = true;
            if (argc > 2 && (!port.hasVendorIdentifier()
                    || port.vendorIdentifier() != QString::fromLocal8Bit(argv[2]).toUInt(nullptr, 16)))
                ++failures;
            if (argc > 3 && (!port.hasProductIdentifier()
                    || port.productIdentifier() != QString::fromLocal8Bit(argv[3]).toUInt(nullptr, 16)))
                ++failures;
            if (argc > 4 && port.serialNumber() != QString::fromLocal8Bit(argv[4]))
                ++failures;
        }
        std::printf("%s|%04x:%04x|%s|%s|%s\n", path.constData(),
                    port.vendorIdentifier(), port.productIdentifier(),
                    qPrintable(port.serialNumber()), qPrintable(port.manufacturer()),
                    qPrintable(port.description()));
    }
    if (!found) {
        std::fprintf(stderr, "expected port missing: %s\n", qPrintable(expected));
        ++failures;
    }
    std::printf("ports=%lld elapsed_ms=%lld failures=%d\n",
                static_cast<long long>(ports.size()), elapsed.elapsed(), failures);
    return failures ? 1 : 0;
}
