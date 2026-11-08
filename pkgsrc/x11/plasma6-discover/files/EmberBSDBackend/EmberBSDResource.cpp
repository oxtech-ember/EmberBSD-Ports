/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */

#include "EmberBSDResource.h"

#include <KLocalizedString>
#include <QFileInfo>
#include <QJsonArray>
#include <QLocale>
#include <QProcess>

namespace {
QString canonicalInside(const QString &prefix, const QString &path)
{
    const QString root = QFileInfo(prefix).canonicalFilePath();
    const QFileInfo info(path);
    const QString canonical = info.canonicalFilePath();
    if (root.isEmpty() || canonical.isEmpty() || !info.isFile())
        return {};
    if (canonical != root && !canonical.startsWith(root + QLatin1Char('/')))
        return {};
    return canonical;
}

// Signed catalog rows carry PKGPATH, PKGNAME and catalog_role. A missing
// desktop file is not enough: libraries, the Plasma SDK and the Wayland
// scanner also have none. These names are that signed identity.
const QStringList plasmaLibraryOrSdk = {
    QStringLiteral("plasma6-kdecoration"),
    QStringLiteral("plasma6-kpipewire"),
    QStringLiteral("plasma6-kwayland"),
    QStringLiteral("plasma6-kwin-qtwaylandscanner"),
    QStringLiteral("plasma6-layer-shell-qt"),
    QStringLiteral("plasma6-plasma-activities"),
    QStringLiteral("plasma6-plasma-activities-stats"),
    QStringLiteral("plasma6-plasma-sdk"),
    QStringLiteral("plasma6-plasma5support"),
    QStringLiteral("plasma6-qqc2-breeze-style"),
    QStringLiteral("plasma6-union"),
};

bool isPlasmaComponent(const QString &base, const QString &catalogRole)
{
    if (catalogRole == QLatin1String("library") || catalogRole == QLatin1String("desktop"))
        return false;
    if (!base.startsWith(QLatin1String("plasma6-")) || base.startsWith(QLatin1String("plasma6-lib")))
        return false;
    return !plasmaLibraryOrSdk.contains(base);
}

QString localizedValue(const QJsonObject &values)
{
    const QStringList languages = QLocale().uiLanguages();
    for (QString language : languages) {
        language.replace(QLatin1Char('-'), QLatin1Char('_'));
        const QString exact = values.value(language).toString();
        if (!exact.isEmpty())
            return exact;
        const QString base = values.value(language.section(QLatin1Char('_'), 0, 0)).toString();
        if (!base.isEmpty())
            return base;
    }
    return values.value(QStringLiteral("C")).toString();
}
}

EmberBSDResource::EmberBSDResource(const QJsonObject &package, const QJsonObject &desktop, const QString &releaseId, AbstractResourcesBackend *parent)
    : AbstractResource(parent)
    , m_packageId(package.value(QStringLiteral("base")).toString())
    , m_version(package.value(QStringLiteral("version")).toString())
    , m_root(package.value(QStringLiteral("root")).toString())
    , m_role(package.value(QStringLiteral("catalog_role")).toString(package.value(QStringLiteral("role")).toString()))
    , m_action(package.value(QStringLiteral("action")).toString())
    , m_installedPackage(package.value(QStringLiteral("installed_pkgname")).toString())
    , m_releaseId(releaseId)
    , m_prefix(package.value(QStringLiteral("prefix")).toString())
    , m_size(static_cast<quint64>(package.value(QStringLiteral("size")).toDouble()))
{
    if (m_action == QLatin1String("upgrade"))
        m_state = Upgradeable;
    else if (m_action == QLatin1String("available"))
        m_state = None;
    else if (m_action == QLatin1String("installed") || m_action == QLatin1String("installed-newer") || m_action == QLatin1String("version-uncompared"))
        m_state = Installed;

    if (!desktop.isEmpty()) {
        const QString relative = desktop.value(QStringLiteral("file")).toString();
        const QString desktopPath = canonicalInside(m_prefix, m_prefix + QLatin1Char('/') + relative);
        const bool desktopLocation = !relative.contains(QLatin1String("..")) && relative.startsWith(QLatin1String("share/applications/")) && relative.endsWith(QLatin1String(".desktop"))
            && desktopPath.startsWith(QFileInfo(m_prefix).canonicalFilePath() + QStringLiteral("/share/applications/"));
        QStringList exec;
        const QJsonArray argv = desktop.value(QStringLiteral("exec")).toArray();
        for (const QJsonValue &value : argv) {
            const QString arg = value.toString();
            if (arg.isEmpty() || arg.contains(QLatin1Char('\n')) || arg.contains(QChar::Null)) {
                exec.clear();
                break;
            }
            exec.append(arg);
        }
        QString program;
        if (!exec.isEmpty())
            program = canonicalInside(m_prefix, exec.first());
        const QString name = localizedValue(desktop.value(QStringLiteral("names")).toObject());
        const QString fallbackName = desktop.value(QStringLiteral("name")).toString();
        if (desktopLocation && !program.isEmpty() && QFileInfo(program).isExecutable() && !(name.isEmpty() && fallbackName.isEmpty())) {
            exec[0] = program;
            m_desktop = true;
            m_role = QStringLiteral("desktop");
            m_desktopId = desktop.value(QStringLiteral("id")).toString();
            if (m_desktopId.isEmpty())
                m_desktopId = QFileInfo(relative).completeBaseName();
            m_name = name.isEmpty() ? fallbackName : name;
            m_comment = desktop.value(QStringLiteral("comment")).toString();
            m_desktopFile = relative;
            m_desktopPackage = desktop.value(QStringLiteral("pkgname")).toString();
            m_exec = exec;
            const QString icon = desktop.value(QStringLiteral("icon")).toString();
            if (icon.contains(QLatin1Char('/')))
                m_icon = canonicalInside(m_prefix, icon);
            else if (!icon.isEmpty() && !icon.contains(QLatin1String("..")))
                m_icon = icon;
            for (const QJsonValue &category : desktop.value(QStringLiteral("categories")).toArray()) {
                const QString text = category.toString();
                if (!text.isEmpty() && !text.contains(QLatin1Char('/')) && !text.contains(QLatin1Char('\n')))
                    m_categories.append(text);
            }
        }
    }
    const QString catalogRole = package.value(QStringLiteral("catalog_role")).toString(package.value(QStringLiteral("role")).toString());
    m_component = !m_desktop && isPlasmaComponent(m_packageId, catalogRole);
}

QString EmberBSDResource::packageName() const
{
    return m_packageId;
}

QString EmberBSDResource::name() const
{
    return m_desktop ? m_name : m_packageId;
}

QString EmberBSDResource::comment()
{
    if (m_desktop && !m_comment.isEmpty())
        return m_comment;
    return m_root;
}

QString EmberBSDResource::longDescription()
{
    if (m_desktop) {
        return i18n("Desktop file %1 from installed package %2, catalog root %3, signed current %4. The name and icon come from that file. The signed catalog records the package only.",
                    m_desktopFile,
                    m_desktopPackage,
                    m_root,
                    m_releaseId);
    }
    if (m_component) {
        return i18n("Plasma component %1 from signed catalog %2, root %3. No standalone desktop launcher is recorded. Install and remove stay unavailable.",
                    m_version,
                    m_releaseId,
                    m_root);
    }
    return i18n("Signed package %1 from %2. Catalog root %3. This is not a desktop application.", m_version, m_releaseId, m_root);
}

QString EmberBSDResource::appstreamId() const
{
    return m_desktop ? m_desktopId : QStringLiteral("package:") + m_packageId;
}

QVariant EmberBSDResource::icon() const
{
    return m_icon.isEmpty() ? QStringLiteral("package-x-generic") : m_icon;
}

AbstractResource::Type EmberBSDResource::type() const
{
    if (m_desktop)
        return Application;
    if (m_role == QLatin1String("library"))
        return System;
    return ApplicationSupport;
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
    return m_desktop && !m_exec.isEmpty() && (m_state == Installed || m_state == Upgradeable);
}

void EmberBSDResource::invokeApplication() const
{
    if (!canExecute())
        return;
    QProcess::startDetached(m_exec.first(), m_exec.mid(1));
}

AbstractResource::State EmberBSDResource::state()
{
    return m_state;
}

bool EmberBSDResource::hasCategory(const QString &category) const
{
    if (category == QLatin1String("packages"))
        return true;
    if (category == QLatin1String("components"))
        return m_component;
    if (!m_desktop)
        return false;
    if (category == QLatin1String("desktop") || category == QLatin1String("applications"))
        return true;
    return m_categories.contains(category);
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
    return QUrl(QStringLiteral("appstream://") + appstreamId());
}

bool EmberBSDResource::isDesktop() const
{
    return m_desktop;
}

bool EmberBSDResource::isComponent() const
{
    return m_component;
}

QString EmberBSDResource::packageRoot() const
{
    return m_root;
}

QString EmberBSDResource::catalogAction() const
{
    return m_action;
}

bool EmberBSDResource::matchesText(const QString &text) const
{
    const QString note = (m_desktop && !m_comment.isEmpty()) ? m_comment : m_root;
    return name().contains(text, Qt::CaseInsensitive) || packageName().contains(text, Qt::CaseInsensitive) || note.contains(text, Qt::CaseInsensitive)
        || appstreamId().contains(text, Qt::CaseInsensitive);
}
