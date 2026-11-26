/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */
#pragma once

#include <QFileSystemWatcher>
#include <QJsonObject>
#include <QTimer>

class EmberUpdateState : public QObject
{
    Q_OBJECT
public:
    explicit EmberUpdateState(QObject *parent = nullptr, const QString &path = QStringLiteral("/var/db/ember-update/state.json"));
    void refresh();
    const QJsonObject &value() const { return m_value; }
    QString description(bool fullPackageList = false) const;
    bool canApply() const;
    bool needsReboot() const;
    static QJsonObject parse(const QByteArray &bytes);

Q_SIGNALS:
    void changed();

private:
    const QString m_path;
    QFileSystemWatcher m_watcher;
    QTimer m_timer;
    QJsonObject m_value;
};
