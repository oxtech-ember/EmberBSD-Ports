/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 *
 * NetBSD envstat reports charge and AC state. It does not expose a
 * charge-threshold or conservation-mode control.
 */

#include "chargethresholdhelper.h"

#include <KAuth/HelperSupport>

namespace
{
ActionReply unsupported()
{
    auto reply = ActionReply::HelperErrorReply();
    reply.setErrorDescription(QStringLiteral("NetBSD does not provide a battery charge threshold interface"));
    return reply;
}
}

ChargeThresholdHelper::ChargeThresholdHelper(QObject *parent)
    : QObject(parent)
{
}

ActionReply ChargeThresholdHelper::getthreshold(const QVariantMap &args)
{
    Q_UNUSED(args);
    return unsupported();
}

ActionReply ChargeThresholdHelper::setthreshold(const QVariantMap &args)
{
    Q_UNUSED(args);
    return unsupported();
}

ActionReply ChargeThresholdHelper::getconservationmode(const QVariantMap &args)
{
    Q_UNUSED(args);
    return unsupported();
}

ActionReply ChargeThresholdHelper::setconservationmode(const QVariantMap &args)
{
    Q_UNUSED(args);
    return unsupported();
}

KAUTH_HELPER_MAIN("org.kde.powerdevil.chargethresholdhelper", ChargeThresholdHelper)

#include "moc_chargethresholdhelper.cpp"
