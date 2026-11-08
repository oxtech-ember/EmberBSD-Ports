/*
 * SPDX-License-Identifier: LGPL-2.0-only
 */

#ifndef BACKLIGHTHELPER_NETBSD_H
#define BACKLIGHTHELPER_NETBSD_H

#include <QObject>

#include <KAuth/ActionReply>
#include <KAuth/HelperSupport>

using namespace KAuth;

class BacklightHelper : public QObject
{
    Q_OBJECT
public:
    explicit BacklightHelper(QObject *parent = nullptr);

public Q_SLOTS:
    ActionReply brightness(const QVariantMap &args);
    ActionReply brightnessmax(const QVariantMap &args);
    ActionReply setbrightness(const QVariantMap &args);
    ActionReply syspath(const QVariantMap &args);

private:
    int readBrightness() const;
    bool writeBrightness(int brightness) const;

    bool m_isSupported = false;
    QByteArray m_sysctlName;
    int m_maxBrightness = 100;
};

#endif
