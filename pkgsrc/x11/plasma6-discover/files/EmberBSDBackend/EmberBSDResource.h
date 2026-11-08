/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */

#pragma once

#include <resources/AbstractResource.h>

#include <QJsonObject>
#include <QStringList>

class EmberBSDResource : public AbstractResource
{
    Q_OBJECT
public:
    EmberBSDResource(const QJsonObject &package, const QJsonObject &desktop, const QString &releaseId, AbstractResourcesBackend *parent);

    QString packageName() const override;
    QString name() const override;
    QString comment() override;
    QString longDescription() override;
    QString appstreamId() const override;
    QVariant icon() const override;
    Type type() const override;
    QString sourceIcon() const override;
    QDate releaseDate() const override;
    void fetchChangelog() override;
    bool canExecute() const override;
    void invokeApplication() const override;
    State state() override;
    bool hasCategory(const QString &category) const override;
    bool isRemovable() const override;
    QString installedVersion() const override;
    QString availableVersion() const override;
    QString origin() const override;
    QString section() override;
    quint64 size() override;
    QString author() const override;
    QList<PackageState> addonsInformation() override;
    QJsonArray licenses() override;
    QUrl homepage() override;
    QUrl url() const override;
    bool isDesktop() const;
    bool isComponent() const;
    bool matchesText(const QString &text) const;

private:
    bool m_desktop = false;
    bool m_component = false;
    QString m_packageId;
    QString m_version;
    QString m_root;
    QString m_role;
    QString m_action;
    QString m_installedPackage;
    QString m_releaseId;
    QString m_prefix;
    QString m_desktopId;
    QString m_name;
    QString m_comment;
    QString m_icon;
    QString m_desktopFile;
    QString m_desktopPackage;
    QStringList m_exec;
    QStringList m_categories;
    quint64 m_size = 0;
    State m_state = None;
};
