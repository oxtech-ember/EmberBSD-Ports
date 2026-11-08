#pragma once

class QObject {};
class NetworkBackend
{
public:
    explicit NetworkBackend(QObject *) {}
    virtual ~NetworkBackend() = default;
    virtual bool isSupported() = 0;
    virtual void start() = 0;
    virtual void stop() = 0;
    virtual void update() = 0;
    void deviceAdded(void *) {}
};

#define Q_EMIT
