/*
    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#ifndef NETBSDBACKEND_H
#define NETBSDBACKEND_H

#include "backend.h"

class NetBsdMemoryBackend : public MemoryBackend
{
public:
    explicit NetBsdMemoryBackend(KSysGuard::SensorContainer *container);
    void update() override;
};

#endif
