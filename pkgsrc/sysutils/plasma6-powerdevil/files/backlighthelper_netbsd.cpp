/*
 * SPDX-License-Identifier: LGPL-2.0-only
 *
 * NetBSD panel brightness.
 *
 * The panel driver exposes its backlight as the wsdisplay(4) brightness
 * parameter on /dev/ttyE0 (WSDISPLAYIO_GETPARAM / WSDISPLAYIO_SETPARAM
 * with WSDISPLAYIO_PARAM_BRIGHTNESS). When the kernel has no such
 * parameter, ACPI _BCM is the fallback: hw.acpi.acpioutN.brightness in the
 * range 0..100.
 *
 * EmberBSD (AI-assisted).
 */

#include "backlighthelper_netbsd.h"

#include <powerdevil_debug.h>

#include <sys/ioctl.h>
#include <sys/sysctl.h>
#include <sys/types.h>

#include <dev/wscons/wsconsio.h>

#include <fcntl.h>
#include <unistd.h>

#include <QByteArray>
#include <QtGlobal>

namespace
{
const char *const wsdisplayPath = "/dev/ttyE0";

bool readSysctl(const char *name, int *value)
{
    size_t length = sizeof(*value);
    return sysctlbyname(name, value, &length, nullptr, 0) == 0 && length == sizeof(*value);
}

QByteArray firstAcpiOutput()
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

bool wsdisplayParam(unsigned long request, wsdisplay_param *param)
{
    const int fd = open(wsdisplayPath, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        return false;
    }
    param->param = WSDISPLAYIO_PARAM_BRIGHTNESS;
    const int result = ioctl(fd, request, param);
    close(fd);
    return result == 0;
}
}

BacklightHelper::BacklightHelper(QObject *parent)
    : QObject(parent)
{
    wsdisplay_param param{};
    if (wsdisplayParam(WSDISPLAYIO_GETPARAM, &param) && param.max > param.min) {
        m_backend = Backend::Wsdisplay;
        m_minBrightness = param.min;
        m_maxBrightness = param.max;
        return;
    }
    m_sysctlName = firstAcpiOutput();
    if (!m_sysctlName.isEmpty()) {
        m_backend = Backend::AcpiSysctl;
        m_minBrightness = 0;
        m_maxBrightness = 100;
        return;
    }
    qCWarning(POWERDEVIL) << "no wsdisplay brightness parameter and no ACPI output brightness node";
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
    if (m_backend == Backend::None) {
        return ActionReply::HelperErrorReply();
    }
    ActionReply reply;
    reply.addData(QStringLiteral("brightnessmax"), m_maxBrightness);
    return reply;
}

ActionReply BacklightHelper::setbrightness(const QVariantMap &args)
{
    if (m_backend == Backend::None) {
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
    switch (m_backend) {
    case Backend::Wsdisplay: {
        wsdisplay_param param{};
        if (!wsdisplayParam(WSDISPLAYIO_GETPARAM, &param)) {
            return -1;
        }
        return param.curval;
    }
    case Backend::AcpiSysctl: {
        int value = -1;
        if (!readSysctl(m_sysctlName.constData(), &value)) {
            return -1;
        }
        return value;
    }
    case Backend::None:
        break;
    }
    return -1;
}

bool BacklightHelper::writeBrightness(int brightness) const
{
    const int value = qBound(m_minBrightness, brightness, m_maxBrightness);
    switch (m_backend) {
    case Backend::Wsdisplay: {
        wsdisplay_param param{};
        param.min = m_minBrightness;
        param.max = m_maxBrightness;
        param.curval = value;
        return wsdisplayParam(WSDISPLAYIO_SETPARAM, &param);
    }
    case Backend::AcpiSysctl: {
        size_t length = sizeof(value);
        return sysctlbyname(m_sysctlName.constData(), nullptr, nullptr, const_cast<int *>(&value), length) == 0;
    }
    case Backend::None:
        break;
    }
    return false;
}

KAUTH_HELPER_MAIN("org.kde.powerdevil.backlighthelper", BacklightHelper)

#include "moc_backlighthelper_netbsd.cpp"
