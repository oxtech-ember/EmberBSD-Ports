/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */
#include "EmberUpdateState.h"

#include <KLocalizedString>
#include <QDateTime>
#include <QLocale>
#include <QMap>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>

namespace {
constexpr qint64 maxBytes = 1024 * 1024;

bool integerOrNull(const QJsonValue &v)
{
    return v.isNull() || (v.isDouble() && v.toInteger(-1) >= 0);
}

bool slotOrNull(const QJsonValue &v)
{
    return v.isNull() || v == QStringLiteral("A") || v == QStringLiteral("B");
}
}

EmberUpdateState::EmberUpdateState(QObject *parent, const QString &path)
    : QObject(parent)
    , m_path(path)
{
    connect(&m_watcher, &QFileSystemWatcher::fileChanged, this, &EmberUpdateState::refresh);
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged, this, &EmberUpdateState::refresh);
    // The service can create its state directory after Discover starts.
    connect(&m_timer, &QTimer::timeout, this, &EmberUpdateState::refresh);
    m_timer.start(30000);
    refresh();
}

QJsonObject EmberUpdateState::parse(const QByteArray &bytes)
{
    const auto s = QJsonDocument::fromJson(bytes).object();
    const auto a = s.value(QStringLiteral("available")).toObject();
    static const QStringList statuses = {QStringLiteral("idle"), QStringLiteral("checking"), QStringLiteral("available"),
        QStringLiteral("preparing"), QStringLiteral("ready"), QStringLiteral("trial"), QStringLiteral("error")};
    const auto hold = s.value(QStringLiteral("os_hold"));
    const auto error = s.value(QStringLiteral("last_error"));
    if (s.value(QStringLiteral("schema")) != QStringLiteral("emberbsd.update-state.v1")
        || !statuses.contains(s.value(QStringLiteral("status")).toString())
        || !integerOrNull(s.value(QStringLiteral("checked_at"))) || !integerOrNull(a.value(QStringLiteral("os_generation")))
        || !a.value(QStringLiteral("packages")).isArray() || !s.value(QStringLiteral("reboot_required")).isBool()
        || !(hold.isNull() || hold == QStringLiteral("custom-kernel")) || !(error.isNull() || error.isString())
        || !slotOrNull(s.value(QStringLiteral("running_slot"))) || !slotOrNull(s.value(QStringLiteral("confirmed_slot"))))
        return {};
    for (const auto &pkg : a.value(QStringLiteral("packages")).toArray()) {
        if (!pkg.isString() || pkg.toString().isEmpty())
            return {};
    }
    return s;
}

void EmberUpdateState::refresh()
{
    const QString dir = QFileInfo(m_path).path();
    if (!m_watcher.directories().contains(dir) && QFileInfo(dir).isDir())
        m_watcher.addPath(dir);
    if (!m_watcher.files().contains(m_path) && QFileInfo(m_path).isFile())
        m_watcher.addPath(m_path);
    QFile file(m_path);
    QJsonObject value;
    if (QFileInfo(m_path).isFile() && file.open(QIODevice::ReadOnly)) {
        const auto bytes = file.read(maxBytes + 1);
        if (bytes.size() <= maxBytes)
            value = parse(bytes);
    }
    if (m_value != value) {
        m_value = value;
        Q_EMIT changed();
    }
}

bool EmberUpdateState::canApply() const
{
    const auto status = m_value.value(QStringLiteral("status")).toString();
    if ((status != QLatin1String("available") && status != QLatin1String("error")) || needsReboot())
        return false;
    const auto available = m_value.value(QStringLiteral("available")).toObject();
    return (!available.value(QStringLiteral("os_generation")).isNull() && m_value.value(QStringLiteral("os_hold")).isNull())
        || !available.value(QStringLiteral("packages")).toArray().isEmpty();
}

bool EmberUpdateState::needsReboot() const
{
    return m_value.value(QStringLiteral("reboot_required")).toBool();
}

QString EmberUpdateState::description(bool fullPackageList) const
{
    const auto &s = value();
    if (s.isEmpty())
        return i18n("System update status is unavailable.");
    const auto status = s.value(QStringLiteral("status")).toString();
    static const QMap<QString, QString> labels = {
        {QStringLiteral("idle"), i18n("No system update is pending.")},
        {QStringLiteral("checking"), i18n("Checking for system updates.")},
        {QStringLiteral("available"), i18n("A system update is available.")},
        {QStringLiteral("preparing"), i18n("Preparing the system update.")},
        {QStringLiteral("ready"), i18n("The system update is ready.")},
        {QStringLiteral("trial"), i18n("The system is testing an update.")},
        {QStringLiteral("error"), i18n("The system update failed.")},
    };
    const auto checked = s.value(QStringLiteral("checked_at"));
    const bool unchecked = checked.isNull() && status == QLatin1String("idle");
    QStringList lines{unchecked ? i18n("No update check has completed yet.") : labels.value(status)};
    const auto available = s.value(QStringLiteral("available")).toObject();
    const auto generation = available.value(QStringLiteral("os_generation"));
    if (!generation.isNull())
        lines << i18n("Available OS generation: %1", generation.toInteger());
    QStringList packages;
    for (const auto &name : available.value(QStringLiteral("packages")).toArray())
        packages << name.toString();
    if (!fullPackageList && packages.size() > 3)
        lines << i18np("%1 package update", "%1 package updates", packages.size());
    else if (!packages.isEmpty())
        lines << i18n("Packages: %1", packages.join(QStringLiteral(", ")));
    if (s.value(QStringLiteral("os_hold")) == QStringLiteral("custom-kernel"))
        lines << i18n("The custom kernel holds OS updates. Package updates remain available.");
    if (needsReboot())
        lines << i18n("A restart is required.");
    const auto running = s.value(QStringLiteral("running_slot")).toString();
    const auto confirmed = s.value(QStringLiteral("confirmed_slot")).toString();
    if (!running.isEmpty())
        lines << i18n("Running slot: %1", running);
    if (!confirmed.isEmpty())
        lines << i18n("Confirmed slot: %1", confirmed);
    if (!checked.isNull())
        lines << i18n("Last checked: %1", QLocale().toString(QDateTime::fromSecsSinceEpoch(checked.toInteger()), QLocale::ShortFormat));
    const auto error = s.value(QStringLiteral("last_error")).toString();
    if (!error.isEmpty())
        lines << error;
    return lines.join(QLatin1Char('\n'));
}

#include "moc_EmberUpdateState.cpp"
