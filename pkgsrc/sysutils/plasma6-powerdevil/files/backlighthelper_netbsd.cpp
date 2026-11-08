/*
 * SPDX-License-Identifier: LGPL-2.0-only
 *
 * NetBSD exposes the panel brightness as hw.acpi.acpioutN.brightness.
 * There is no separate maximum node. The live panel uses the range 0..100.
 */

#include "backlighthelper_netbsd.h"

#include <powerdevil_debug.h>

#include <sys/sysctl.h>
#include <sys/types.h>

#include <QByteArray>
#include <QtGlobal>

namespace
{
bool readSysctl(const char *name, int *value)
{
    size_t length = sizeof(*value);
    return sysctlbyname(name, value, &length, nullptr, 0) == 0 && length == sizeof(*value);
}

QByteArray firstOutput()
{
    for (int index = 0; index < 8; ++index) {
        const QByteArray name = QByteArrayLiteral("hw.acpi.acpiout") + QByteArray::number(index) + QByteArrayLiteral(".brightness");
        int value = 0;
        if (!readSysctl(name.constData(), &value)) {
            break;
        }
        return name;
    }
    return {};
}
}

BacklightHelper::BacklightHelper(QObject *parent)
    : QObject(parent)
{
    m_sysctlName = firstOutput();
    m_isSupported = !m_sysctlName.isEmpty();
    if (!m_isSupported) {
        qCWarning(POWERDEVIL) << "no NetBSD ACPI output brightness node found";
    }
}

ActionReply BacklightHelper::brightness(const QVariantMap &args)
{
    Q_UNUSED(args);
    const int value = readBrightness();
    if (value < 0) {
        return ActionReply::HelperErrorReply();
    }
    ActionReply reply;
    reply.addData(QStringLiteral("brightness"), value);
    return reply;
}

ActionReply BacklightHelper::brightnessmax(const QVariantMap &args)
{
    Q_UNUSED(args);
    if (!m_isSupported) {
        return ActionReply::HelperErrorReply();
    }
    ActionReply reply;
    reply.addData(QStringLiteral("brightnessmax"), m_maxBrightness);
    return reply;
}

ActionReply BacklightHelper::setbrightness(const QVariantMap &args)
{
    if (!m_isSupported) {
        return ActionReply::HelperErrorReply();
    }
    const int value = args.value(QStringLiteral("brightness")).toInt();
    if (!writeBrightness(value)) {
        return ActionReply::HelperErrorReply();
    }
    return ActionReply::SuccessReply();
}

ActionReply BacklightHelper::syspath(const QVariantMap &args)
{
    Q_UNUSED(args);
    return ActionReply::HelperErrorReply();
}

int BacklightHelper::readBrightness() const
{
    if (!m_isSupported) {
        return -1;
    }
    int value = -1;
    if (!readSysctl(m_sysctlName.constData(), &value)) {
        return -1;
    }
    return value;
}

bool BacklightHelper::writeBrightness(int brightness) const
{
    if (!m_isSupported) {
        return false;
    }
    const int value = qBound(0, brightness, m_maxBrightness);
    size_t length = sizeof(value);
    return sysctlbyname(m_sysctlName.constData(), nullptr, nullptr, const_cast<int *>(&value), length) == 0;
}

KAUTH_HELPER_MAIN("org.kde.powerdevil.backlighthelper", BacklightHelper)

#include "moc_backlighthelper_netbsd.cpp"
