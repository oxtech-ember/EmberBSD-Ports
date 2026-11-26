/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */
#include "EmberUpdateState.h"

#include <BackendNotifierModule.h>

class EmberBSDNotifier : public BackendNotifierModule
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID DISCOVER_NOTIFIER_IID)
    Q_INTERFACES(BackendNotifierModule)
    Q_PROPERTY(QString emberUpdateStatus READ emberUpdateStatus NOTIFY foundUpdates)
public:
    explicit EmberBSDNotifier(QObject *parent = nullptr)
        : BackendNotifierModule(parent)
    {
        connect(&m_state, &EmberUpdateState::changed, this, &BackendNotifierModule::foundUpdates);
    }

    QString emberUpdateStatus() const { return m_state.description(); }
    void recheckSystemUpdateNeeded() override { m_state.refresh(); }
    bool hasUpdates() override { return m_state.canApply(); }
    bool hasSecurityUpdates() override { return false; }
    bool needsReboot() const override { return m_state.needsReboot(); }

private:
    EmberUpdateState m_state;
};

#include "EmberBSDNotifier.moc"
