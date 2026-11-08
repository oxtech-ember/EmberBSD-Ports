/*
    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#pragma once

#include "NetworkBackend.h"
#include "NetworkDevice.h"

#include <QElapsedTimer>
#include <QHash>

class IfaddrsNetDevice : public NetworkDevice
{
public:
    IfaddrsNetDevice(const QString &id, const QString &name);
    void update();

private:
    bool m_haveSample = false;
    quint64 m_previousDownload = 0;
    quint64 m_previousUpload = 0;
    QElapsedTimer m_timer;
};

class NetBsdNetworkBackend : public NetworkBackend
{
public:
    explicit NetBsdNetworkBackend(QObject *parent);
    ~NetBsdNetworkBackend() override;
    bool isSupported() override;
    void start() override;
    void stop() override;
    void update() override;

private:
    QHash<QByteArray, IfaddrsNetDevice *> m_devices;
};
