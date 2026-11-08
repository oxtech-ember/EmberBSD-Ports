/*
    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#include "netbsdcpuplugin.h"

#include "loadaverages.h"

#include <algorithm>
#include <climits>

#include <sys/sched.h>
#include <sys/sysctl.h>
#include <sys/types.h>

#include <KLocalizedString>

#include <QVariant>

#include <systemstats/SensorContainer.h>

namespace
{
bool readSysctl(const char *name, void *buffer, size_t size)
{
    return sysctlbyname(name, buffer, &size, nullptr, 0) == 0;
}

bool readTicks(const char *name, uint64_t ticks[CPUSTATES])
{
    size_t size = sizeof(uint64_t) * CPUSTATES;
    return sysctlbyname(name, ticks, &size, nullptr, 0) == 0 && size == sizeof(uint64_t) * CPUSTATES;
}

int currentFrequencyMhz()
{
    int mhz = 0;
    size_t size = sizeof(mhz);
    if (sysctlbyname("machdep.cpu.frequency.current", &mhz, &size, nullptr, 0) != 0 || size != sizeof(mhz) || mhz <= 0) {
        return 0;
    }
    return mhz;
}

void applyFrequencyRange(KSysGuard::SensorProperty *sensor)
{
    char text[256];
    size_t size = sizeof(text);
    if (sysctlbyname("machdep.cpu.frequency.available", text, &size, nullptr, 0) != 0 || size < 2) {
        return;
    }
    text[sizeof(text) - 1] = '\0';
    int minimum = INT_MAX;
    int maximum = 0;
    const QStringList levels = QString::fromLatin1(text).split(QLatin1Char(' '), Qt::SkipEmptyParts);
    for (const QString &level : levels) {
        bool ok = false;
        const int mhz = level.toInt(&ok);
        if (!ok || mhz <= 0) {
            continue;
        }
        minimum = std::min(minimum, mhz);
        maximum = std::max(maximum, mhz);
    }
    if (maximum > 0 && minimum != INT_MAX) {
        sensor->setMin(minimum);
        sensor->setMax(maximum);
    }
}
}

NetBsdCpuObject::NetBsdCpuObject(int cpuNumber, const QString &name, KSysGuard::SensorContainer *parent)
    : CpuObject(QStringLiteral("cpu%1").arg(cpuNumber), name, parent)
{
}

void NetBsdCpuObject::makeSensors()
{
    BaseCpuObject::makeSensors();
    m_frequency = new KSysGuard::SensorProperty(QStringLiteral("frequency"), QStringLiteral("frequency"), this);
}

void NetBsdCpuObject::initialize()
{
    BaseCpuObject::initialize();
    // NetBSD kern.cp_time has no iowait state. Leave the inherited wait sensor empty.
    m_wait->setValue(QVariant());

    m_frequency->setPrefix(name());
    m_frequency->setName(i18nc("@title", "Current Frequency"));
    m_frequency->setShortName(i18nc("@title, Short for 'Current Frequency'", name().toUtf8().constData()));
    m_frequency->setDescription(i18nc("@info", "Current CPU package frequency from machdep.cpu.frequency.current"));
    m_frequency->setVariantType(QVariant::Double);
    m_frequency->setUnit(KSysGuard::Unit::UnitMegaHertz);
    applyFrequencyRange(m_frequency);
}

void NetBsdCpuObject::update(unsigned long long system, unsigned long long user, unsigned long long idle)
{
    m_usageComputer.setTicks(static_cast<long long>(system), static_cast<long long>(user), 0, static_cast<long long>(idle));
    m_system->setValue(m_usageComputer.systemUsage);
    m_user->setValue(m_usageComputer.userUsage);
    m_usage->setValue(m_usageComputer.totalUsage);
    if (!isSubscribed()) {
        return;
    }
    const int mhz = currentFrequencyMhz();
    if (mhz > 0) {
        m_frequency->setValue(mhz);
    }
}

void NetBsdAllCpusObject::setLogicalCpuCount(int count)
{
    m_cpuCount->setValue(count);
}

void NetBsdAllCpusObject::update(unsigned long long system, unsigned long long user, unsigned long long idle)
{
    m_usageComputer.setTicks(static_cast<long long>(system), static_cast<long long>(user), 0, static_cast<long long>(idle));
    m_system->setValue(m_usageComputer.systemUsage);
    m_user->setValue(m_usageComputer.userUsage);
    m_usage->setValue(m_usageComputer.totalUsage);
}

NetBsdCpuPluginPrivate::NetBsdCpuPluginPrivate(CpuPlugin *q)
    : CpuPluginPrivate(q)
{
    m_loadAverages = new LoadAverages(m_container);
    int cpuCount = 0;
    readSysctl("hw.ncpu", &cpuCount, sizeof(cpuCount));
    for (int cpu = 0; cpu < cpuCount; ++cpu) {
        auto object = new NetBsdCpuObject(cpu, i18nc("@title", "CPU %1", cpu + 1), m_container);
        object->initialize();
        m_cpus.append(object);
    }
    m_allCpus = new NetBsdAllCpusObject(m_container);
    m_allCpus->initialize();
    if (cpuCount > 0) {
        m_allCpus->setLogicalCpuCount(cpuCount);
    }
    update();
}

void NetBsdCpuPluginPrivate::update()
{
    m_loadAverages->update();
    const auto subscribed = [](const KSysGuard::SensorObject *object) {
        return object->isSubscribed();
    };
    if (std::none_of(m_cpus.cbegin(), m_cpus.cend(), subscribed) && !m_allCpus->isSubscribed()) {
        return;
    }

    for (int index = 0; index < m_cpus.count(); ++index) {
        uint64_t ticks[CPUSTATES];
        const QByteArray name = QByteArrayLiteral("kern.cp_time.") + QByteArray::number(index);
        if (!readTicks(name.constData(), ticks)) {
            continue;
        }
        m_cpus[index]->update(ticks[CP_SYS] + ticks[CP_INTR], ticks[CP_USER] + ticks[CP_NICE], ticks[CP_IDLE]);
    }

    uint64_t total[CPUSTATES];
    if (readTicks("kern.cp_time", total)) {
        m_allCpus->update(total[CP_SYS] + total[CP_INTR], total[CP_USER] + total[CP_NICE], total[CP_IDLE]);
    }
}
