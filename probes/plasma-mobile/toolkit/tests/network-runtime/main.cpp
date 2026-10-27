// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Check native TLS backend loading without a connection.
#include <QCoreApplication>
#include <QSslSocket>
#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    if (!QSslSocket::supportsSsl()) {
        std::fputs("Qt Network TLS backend unavailable\n", stderr);
        return 1;
    }
    std::printf("TLS runtime: %s\n", qPrintable(QSslSocket::sslLibraryVersionString()));
    return 0;
}
