/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */

#include "EmberBSDResource.h"

#include <KLocalizedString>

EmberBSDResource::EmberBSDResource(QString packageId, QString version, bool installed, quint64 size, QString releaseId, AbstractResourcesBackend *parent)
    : AbstractResource(parent)
    , m_packageId(std::move(packageId))
    , m_version(std::move(version))
    , m_state(installed ? Installed : None)
    , m_size(size)
    , m_releaseId(std::move(releaseId))
{
}

QString EmberBSDResource::packageName() const
{
    return m_packageId;
}

QString EmberBSDResource::name() const
{
    return i18n("Ember Browser");
}

QString EmberBSDResource::comment()
{
    return i18n("Signed package %1", m_version);
}

QString EmberBSDResource::longDescription()
{
    return i18n("Signed current release %1. Catalog root www/blanc. Package %2 is %3. Install and remove stay unavailable until a verified helper exists.",
                m_releaseId,
                m_packageId,
                m_state == Installed ? i18n("installed") : i18n("not installed"));
}

QVariant EmberBSDResource::icon() const
{
    return QStringLiteral("internet-web-browser");
}

AbstractResource::Type EmberBSDResource::type() const
{
    return Application;
}

QString EmberBSDResource::sourceIcon() const
{
    return QStringLiteral("internet-web-browser");
}

QDate EmberBSDResource::releaseDate() const
{
    return {};
}

void EmberBSDResource::fetchChangelog()
{
}

bool EmberBSDResource::canExecute() const
{
    return false;
}

void EmberBSDResource::invokeApplication() const
{
}

AbstractResource::State EmberBSDResource::state()
{
    return m_state;
}

bool EmberBSDResource::hasCategory(const QString &category) const
{
    return category == QLatin1String("emberbsd");
}

bool EmberBSDResource::isRemovable() const
{
    return false;
}

QString EmberBSDResource::installedVersion() const
{
    return m_state == Installed ? m_version : QString();
}

QString EmberBSDResource::availableVersion() const
{
    return m_version;
}

QString EmberBSDResource::origin() const
{
    return QStringLiteral("netbsd-amd64");
}

QString EmberBSDResource::section()
{
    return QStringLiteral("www");
}

quint64 EmberBSDResource::size()
{
    return m_size;
}

QString EmberBSDResource::author() const
{
    return QStringLiteral("EmberBSD");
}

QList<PackageState> EmberBSDResource::addonsInformation()
{
    return {};
}

QJsonArray EmberBSDResource::licenses()
{
    return {};
}

QUrl EmberBSDResource::homepage()
{
    return {};
}

QUrl EmberBSDResource::url() const
{
    return QUrl(QStringLiteral("appstream://") + m_packageId);
}
