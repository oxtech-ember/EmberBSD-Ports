// SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
//
// NetBSD has no systemd user unit. Classify free RAM with KMemoryInfo and
// do not call systemd SetProperties.

#include "memoryfence.h"

#include <KMemoryInfo>

#include "drkonqi_debug.h"

using namespace Qt::StringLiterals;

void MemoryFence::surroundMe()
{
    const auto available = freeRAM();
    if (!available) {
        Q_EMIT loaded();
        return;
    }
    constexpr auto fallbackCurrent = 512ULL * 1024 * 1024;
    applyProperties(fallbackCurrent, available.value());
}

MemoryFence::Size MemoryFence::size() const
{
    return m_size;
}

bool MemoryFence::registerDBusTypes()
{
    return true;
}

void MemoryFence::getUnit()
{
    Q_EMIT loaded();
}

std::optional<qulonglong> MemoryFence::freeRAM()
{
    KMemoryInfo info;
    if (info.isNull()) {
        return {};
    }
    return info.freePhysical() + info.buffers() + info.cached();
}

void MemoryFence::getMemory()
{
    Q_EMIT loaded();
}

void MemoryFence::applyProperties(qulonglong memoryCurrent, qulonglong memoryAvailable)
{
    Q_UNUSED(memoryCurrent);
    constexpr auto GiB = 1024ULL * 1024 * 1024;
    if (memoryAvailable > GiB) {
        memoryAvailable -= GiB;
    }
    const auto memoryAvailableGiB = memoryAvailable / GiB;
    constexpr auto lotsGiB = 12;
    constexpr auto someGiB = 4;
    constexpr auto littleGiB = 2;
    if (memoryAvailableGiB > lotsGiB) {
        m_size = Size::Spacious;
    } else if (memoryAvailableGiB > someGiB) {
        m_size = Size::Some;
    } else if (memoryAvailableGiB > littleGiB) {
        m_size = Size::Little;
    } else {
        m_size = Size::Cramped;
    }
    qCDebug(DRKONQI_LOG) << "NetBSD free-RAM class" << static_cast<int>(m_size);
    Q_EMIT sizeChanged();
    Q_EMIT loaded();
}

#include "moc_memoryfence.cpp"
