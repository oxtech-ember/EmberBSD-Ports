/*
    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#include "NetBsdBackend.h"

#include <ifaddrs.h>
#include <net/if.h>
#include <net/if_types.h>
#include <netdb.h>
#include <sys/socket.h>

#include <QSet>

#include <systemstats/SensorProperty.h>

namespace
{
bool isPhysicalInterface(const if_data *data)
{
    return data != nullptr && (data->ifi_type == IFT_ETHER || data->ifi_type == IFT_IEEE80211);
}

void setRate(KSysGuard::SensorProperty *bytesPerSecond, KSysGuard::SensorProperty *bitsPerSecond, quint64 delta, qint64 elapsedMs)
{
    if (elapsedMs <= 0) {
        return;
    }
    const quint64 bytes = delta * 1000 / static_cast<quint64>(elapsedMs);
    bytesPerSecond->setValue(bytes);
    bitsPerSecond->setValue(bytes * 8);
}
}

IfaddrsNetDevice::IfaddrsNetDevice(const QString &id, const QString &name)
    : NetworkDevice(id, name)
{
    m_networkSensor->setValue(id);
    m_timer.start();
}

void IfaddrsNetDevice::update()
{
    ifaddrs *list = nullptr;
    if (getifaddrs(&list) != 0) {
        return;
    }

    QStringList ipv4;
    QStringList ipv6;
    const if_data *data = nullptr;
    for (ifaddrs *item = list; item != nullptr; item = item->ifa_next) {
        if (item->ifa_name == nullptr || name() != QString::fromLatin1(item->ifa_name) || item->ifa_addr == nullptr) {
            continue;
        }
        if (item->ifa_addr->sa_family == AF_LINK && data == nullptr) {
            data = static_cast<const if_data *>(item->ifa_data);
            continue;
        }
        char host[NI_MAXHOST];
        const socklen_t length = item->ifa_addr->sa_len;
        if (getnameinfo(item->ifa_addr, length, host, sizeof(host), nullptr, 0, NI_NUMERICHOST) != 0) {
            continue;
        }
        if (item->ifa_addr->sa_family == AF_INET) {
            ipv4.append(QString::fromLatin1(host));
        } else if (item->ifa_addr->sa_family == AF_INET6) {
            ipv6.append(QString::fromLatin1(host));
        }
    }
    freeifaddrs(list);

    m_ipv4Sensor->setValue(ipv4.join(QLatin1Char('\n')));
    m_ipv6Sensor->setValue(ipv6.join(QLatin1Char('\n')));
    if (data == nullptr) {
        return;
    }

    const quint64 download = data->ifi_ibytes;
    const quint64 upload = data->ifi_obytes;
    if (m_haveSample) {
        const qint64 elapsed = m_timer.elapsed();
        if (download >= m_previousDownload) {
            setRate(m_downloadSensor, m_downloadBitsSensor, download - m_previousDownload, elapsed);
        }
        if (upload >= m_previousUpload) {
            setRate(m_uploadSensor, m_uploadBitsSensor, upload - m_previousUpload, elapsed);
        }
    }
    m_totalDownloadSensor->setValue(download);
    m_totalUploadSensor->setValue(upload);
    m_previousDownload = download;
    m_previousUpload = upload;
    m_haveSample = true;
    m_timer.restart();
}

NetBsdNetworkBackend::NetBsdNetworkBackend(QObject *parent)
    : NetworkBackend(parent)
{
}

NetBsdNetworkBackend::~NetBsdNetworkBackend()
{
    qDeleteAll(m_devices);
}

bool NetBsdNetworkBackend::isSupported()
{
    return true;
}

void NetBsdNetworkBackend::start()
{
    ifaddrs *list = nullptr;
    if (getifaddrs(&list) != 0) {
        return;
    }
    QSet<QByteArray> seen;
    for (ifaddrs *item = list; item != nullptr; item = item->ifa_next) {
        if (item->ifa_name == nullptr || item->ifa_addr == nullptr || item->ifa_addr->sa_family != AF_LINK) {
            continue;
        }
        if (!isPhysicalInterface(static_cast<const if_data *>(item->ifa_data))) {
            continue;
        }
        const QByteArray id(item->ifa_name);
        if (seen.contains(id)) {
            continue;
        }
        seen.insert(id);
        const QString name = QString::fromLatin1(id);
        auto *device = new IfaddrsNetDevice(name, name);
        m_devices.insert(id, device);
        Q_EMIT deviceAdded(device);
    }
    freeifaddrs(list);
}

void NetBsdNetworkBackend::stop()
{
}

void NetBsdNetworkBackend::update()
{
    for (IfaddrsNetDevice *device : m_devices) {
        device->update();
    }
}
