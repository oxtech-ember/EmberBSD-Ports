// SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
//
// Linux PSI and sd-event are not available. The level stays at its initial
// value and is not reported as a measurement.

#include "memorypressure.h"

MemoryPressure::~MemoryPressure() = default;

void MemoryPressure::reset()
{
}

MemoryPressure::Level MemoryPressure::level() const
{
    return m_level;
}

MemoryPressure::MemoryPressure(QObject *parent)
    : QObject(parent)
    , m_monitor(nullptr)
{
}

MemoryPressure *MemoryPressure::instance()
{
    static MemoryPressure object;
    return &object;
}

#include "moc_memorypressure.cpp"
