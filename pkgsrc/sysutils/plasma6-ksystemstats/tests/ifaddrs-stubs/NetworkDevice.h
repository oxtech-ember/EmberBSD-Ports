#pragma once

#include "QString"
#include "QStringList"
#include <systemstats/SensorProperty.h>

class NetworkDevice
{
public:
    NetworkDevice(const QString &, const QString &deviceName) : deviceName(deviceName) {}
    virtual ~NetworkDevice() = default;
    const QString &name() const { return deviceName; }

    KSysGuard::SensorProperty *m_networkSensor = &network;
    KSysGuard::SensorProperty *m_ipv4Sensor = &ipv4;
    KSysGuard::SensorProperty *m_ipv6Sensor = &ipv6;
    KSysGuard::SensorProperty *m_downloadSensor = &download;
    KSysGuard::SensorProperty *m_downloadBitsSensor = &downloadBits;
    KSysGuard::SensorProperty *m_uploadSensor = &upload;
    KSysGuard::SensorProperty *m_uploadBitsSensor = &uploadBits;
    KSysGuard::SensorProperty *m_totalDownloadSensor = &totalDownload;
    KSysGuard::SensorProperty *m_totalUploadSensor = &totalUpload;
private:
    QString deviceName;
    KSysGuard::SensorProperty network, ipv4, ipv6, download, downloadBits;
    KSysGuard::SensorProperty upload, uploadBits, totalDownload, totalUpload;
};
