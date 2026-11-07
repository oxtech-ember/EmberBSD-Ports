/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */

#pragma once

#include <resources/AbstractResource.h>

class EmberBSDResource : public AbstractResource
{
    Q_OBJECT
public:
    EmberBSDResource(QString packageId, QString version, QString root, QString role, QString action, QString installedPackage, quint64 size, QString releaseId, AbstractResourcesBackend *parent);

    QString packageName() const override;
    QString name() const override;
    QString comment() override;
    QString longDescription() override;
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
    bool isLibrary() const;

private:
    QString m_packageId;
    QString m_version;
    QString m_root;
    QString m_role;
    QString m_action;
    QString m_installedPackage;
    quint64 m_size;
    QString m_releaseId;
    State m_state;
};
