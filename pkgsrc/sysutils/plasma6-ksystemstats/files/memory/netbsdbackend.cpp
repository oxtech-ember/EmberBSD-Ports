/*
    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#include "netbsdbackend.h"

#include <sys/sysctl.h>
#include <sys/types.h>
#include <uvm/uvm_extern.h>
#include <uvm/uvm_param.h>

#include <systemstats/SensorProperty.h>

namespace
{
bool readUvm(uvmexp_sysctl *stats)
{
    int name[] = {CTL_VM, VM_UVMEXP2};
    size_t size = sizeof(*stats);
    return sysctl(name, 2, stats, &size, nullptr, 0) == 0 && size >= sizeof(*stats);
}

unsigned long long pagesToBytes(int64_t pages, int64_t pageSize)
{
    if (pages < 0 || pageSize <= 0) {
        return 0;
    }
    return static_cast<unsigned long long>(pages) * static_cast<unsigned long long>(pageSize);
}
}

NetBsdMemoryBackend::NetBsdMemoryBackend(KSysGuard::SensorContainer *container)
    : MemoryBackend(container)
{
}

void NetBsdMemoryBackend::update()
{
    uvmexp_sysctl stats{};
    if (!readUvm(&stats) || stats.pagesize <= 0 || stats.npages <= 0 || stats.free < 0 || stats.free > stats.npages) {
        return;
    }

    const unsigned long long total = pagesToBytes(stats.npages, stats.pagesize);
    const unsigned long long free = pagesToBytes(stats.free, stats.pagesize);
    m_total->setValue(total);
    m_free->setValue(free);
    m_used->setValue(total - free);
    if (stats.anonpages >= 0) {
        m_application->setValue(pagesToBytes(stats.anonpages, stats.pagesize));
    }
    if (stats.filepages >= 0) {
        m_cache->setValue(pagesToBytes(stats.filepages, stats.pagesize));
    }
    if (stats.swpages >= 0 && stats.swpginuse >= 0 && stats.swpginuse <= stats.swpages) {
        const unsigned long long swapTotal = pagesToBytes(stats.swpages, stats.pagesize);
        const unsigned long long swapUsed = pagesToBytes(stats.swpginuse, stats.pagesize);
        m_swapTotal->setValue(swapTotal);
        m_swapUsed->setValue(swapUsed);
        m_swapFree->setValue(swapTotal - swapUsed);
    }
}
