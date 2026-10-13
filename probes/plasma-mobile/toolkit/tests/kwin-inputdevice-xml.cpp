// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Check the unchanged Qt D-Bus marshallers.
#include <QtCore/QCoreApplication>
#include <QtCore/QList>
#include <QtCore/QRectF>
#include <QtCore/QSizeF>
#include <QtDBus/QDBusArgument>
#include <QtDBus/QDBusMetaType>
#include <cstdio>
#include <cstring>

template<typename T>
static bool check(const char *name, const char *expected, const T &value)
{
    const char *signature = QDBusMetaType::typeToSignature(qDBusRegisterMetaType<T>());
    if (!signature || std::strcmp(signature, expected) != 0) {
        std::fprintf(stderr, "FAIL: %s metatype signature\n", name);
        return false;
    }
    QDBusArgument argument;
    argument << value;
    if (argument.currentSignature() != QString::fromLatin1(expected)) {
        std::fprintf(stderr, "FAIL: %s marshalled signature\n", name);
        return false;
    }
    std::printf("PASS: %s %s\n", name, signature);
    return true;
}

int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    return check("QSizeF", "(dd)", QSizeF(12.5, 34.75))
        && check("QRectF", "(dddd)", QRectF(-1.25, 2.5, 3.75, 4.0))
        && check("QList<uint>", "au", QList<uint>{0U, 1U, 0xffffffffU}) ? 0 : 1;
}
