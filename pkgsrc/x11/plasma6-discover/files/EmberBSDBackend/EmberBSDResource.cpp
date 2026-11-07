/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */

#include "EmberBSDResource.h"

#include <KLocalizedString>

EmberBSDResource::EmberBSDResource(QString packageId, QString version, QString root, QString role, QString action, QString installedPackage, quint64 size, QString releaseId, AbstractResourcesBackend *parent)
    : AbstractResource(parent)
    , m_packageId(std::move(packageId))
    , m_version(std::move(version))
    , m_root(std::move(root))
    , m_role(std::move(role))
    , m_action(std::move(action))
    , m_installedPackage(std::move(installedPackage))
    , m_size(size)
    , m_releaseId(std::move(releaseId))
    , m_state(None)
{
    if (m_action == QLatin1String("upgrade"))
        m_state = Upgradeable;
    else if (m_action == QLatin1String("available"))
        m_state = None;
    else if (m_action == QLatin1String("installed") || m_action == QLatin1String("installed-newer") || m_action == QLatin1String("version-uncompared"))
        m_state = Installed;
}

QString EmberBSDResource::packageName() const
{
    return m_packageId;
}

QString EmberBSDResource::name() const
{
    return m_packageId;
}

QString EmberBSDResource::comment()
{
    return m_root;
}

QString EmberBSDResource::longDescription()
{
    return i18n("Signed package %1 from %2. Catalog root %3. Role %4. State %5. Installed package %6. The signed catalog has no desktop metadata, so this name is the package name.",
                m_version,
                m_releaseId,
                m_root,
                m_role,
                m_action,
                m_installedPackage.isEmpty() ? i18n("none") : m_installedPackage);
}

QVariant EmberBSDResource::icon() const
{
    return QStringLiteral("package-x-generic");
}

AbstractResource::Type EmberBSDResource::type() const
{
    return m_role == QLatin1String("library") ? System : Application;
}

QString EmberBSDResource::sourceIcon() const
{
    return QStringLiteral("package-x-generic");
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
    if (category == QLatin1String("packages"))
        return true;
    if (category == QLatin1String("applications"))
        return !isLibrary();
    return false;
}

bool EmberBSDResource::isRemovable() const
{
    return false;
}

QString EmberBSDResource::installedVersion() const
{
    const int split = m_installedPackage.lastIndexOf(QLatin1Char('-'));
    return split > 0 ? m_installedPackage.mid(split + 1) : QString();
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
    return m_root.section(QLatin1Char('/'), 0, 0);
}

quint64 EmberBSDResource::size()
{
    return m_size;
}

QString EmberBSDResource::author() const
{
    return QString();
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

bool EmberBSDResource::isLibrary() const
{
    return m_role == QLatin1String("library");
}
