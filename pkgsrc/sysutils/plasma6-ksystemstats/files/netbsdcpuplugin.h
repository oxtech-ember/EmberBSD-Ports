/*
    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#ifndef NETBSDCPUPLUGIN_H
#define NETBSDCPUPLUGIN_H

#include "cpu.h"
#include "cpuplugin_p.h"
#include "usagecomputer.h"

class LoadAverages;

class NetBsdCpuObject : public CpuObject
{
public:
    NetBsdCpuObject(int cpuNumber, const QString &name, KSysGuard::SensorContainer *parent);
    void update(unsigned long long system, unsigned long long user, unsigned long long idle);
    void initialize() override;

private:
    void makeSensors() override;
    UsageComputer m_usageComputer;
};

class NetBsdAllCpusObject : public AllCpusObject
{
public:
    using AllCpusObject::AllCpusObject;
    void setLogicalCpuCount(int count);
    void update(unsigned long long system, unsigned long long user, unsigned long long idle);

private:
    UsageComputer m_usageComputer;
};

class NetBsdCpuPluginPrivate : public CpuPluginPrivate
{
public:
    explicit NetBsdCpuPluginPrivate(CpuPlugin *q);
    void update() override;

private:
    NetBsdAllCpusObject *m_allCpus = nullptr;
    QList<NetBsdCpuObject *> m_cpus;
    LoadAverages *m_loadAverages = nullptr;
};

#endif
